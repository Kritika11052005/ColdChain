import os
import sys
import re
import uuid
import asyncio
import datetime
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from models.database import init_db, get_client
from utils.logger import log_to_pipeline
from services.discovery_service import find_lookalike_companies
from services.prospeo_service import find_decision_makers
from utils.deduplicator import deduplicate_contacts
from services.gemini_service import score_lead, personalize_email, generate_company_summary
from services.serper_service import search_company_context, search_company_info
from services.brevo_service import send_outreach_email, SENDER_NAME, SENDER_EMAIL

DOMAIN_PATTERN = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\. )'
    r'+[a-zA-Z]{2,}$'.replace('. ', '.')
)

async def run_cli(seed_domain: str):
    # Initialize DB
    await init_db()
    
    run_id = f"run_cli_{uuid.uuid4().hex[:8]}"
    started_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save running pipeline in DB
    async with get_client() as client:
        await client.execute(
            "INSERT INTO pipeline_runs (id, seed_domain, status, started_at) VALUES (?, ?, ?, ?)",
            [run_id, seed_domain, "RUNNING", started_at]
        )
        
    start_time = datetime.datetime.utcnow()
    
    try:
        await log_to_pipeline(run_id, "INFO", f"ColdChain CLI initiated for domain: {seed_domain}", stage=None)
        
        # --- STAGE 1: Dynamic AI-Powered Company Discovery (Serper + Gemini) ---
        await log_to_pipeline(run_id, "INFO", "[Stage 1] Executing Dynamic AI-Powered Company Discovery...", stage=1)
        companies = await find_lookalike_companies(seed_domain, run_id)
        
        # Empty pipeline guard
        if not companies:
            print("\n" + "=" * 60)
            print(" ERROR: Could not find lookalike companies for this domain.")
            print(" Try a more well-known company.")
            print("=" * 60)
            await log_to_pipeline(run_id, "ERROR", "Could not find lookalike companies for this domain. Try a more well-known company.", stage=1)
            async with get_client() as client:
                await client.execute(
                    "UPDATE pipeline_runs SET status = 'ERROR', error_message = ? WHERE id = ?",
                    ["Could not find lookalike companies for this domain. Try a more well-known company.", run_id]
                )
            return
            
        async with get_client() as client:
            for comp in companies:
                comp_id = f"comp_{uuid.uuid4()}"
                comp["id"] = comp_id
                await client.execute(
                    "INSERT INTO companies (id, run_id, domain, name, industry, employee_count, country, description, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [comp_id, run_id, comp["domain"], comp.get("name"), comp.get("industry"), comp.get("employee_count"), comp.get("country"), comp.get("description"), comp.get("source", "serper_gemini")]
                )
            await client.execute("UPDATE pipeline_runs SET companies_found = ? WHERE id = ?", [len(companies), run_id])
            
        # --- STAGE 2: Decision Maker Discovery (Prospeo) ---
        await log_to_pipeline(run_id, "INFO", f"[Stage 2] Sourcing decision makers via Prospeo for {len(companies)} lookalike companies...", stage=2)
        all_prospects = []
        for comp in companies:
            domain = comp["domain"]
            name = comp.get("name") or domain
            await log_to_pipeline(run_id, "INFO", f"[Stage 2] Sourcing decision makers for {name} ({domain})...", stage=2)
            prospects = await find_decision_makers(domain, run_id)
            for p in prospects:
                p["company_id"] = comp["id"]
                p["company_name"] = comp.get("name")
            all_prospects.extend(prospects)
            
        if not all_prospects:
            raise Exception("No prospects sourced. CLI pipeline stopped.")
            
        async with get_client() as client:
            await client.execute("UPDATE pipeline_runs SET prospects_found = ? WHERE id = ?", [len(all_prospects), run_id])
            
        # --- STAGE 3: AI Lead Scoring (Gemini) ---
        # Skip contacts without emails in Stage 3
        all_prospects = [p for p in all_prospects if p.get("email")]
        
        # Deduplicate contacts by email before scoring
        all_prospects = deduplicate_contacts(all_prospects)
        
        # Generate company summaries via Serper + Gemini
        company_summaries = {}
        unique_companies = {p.get("company_domain"): p.get("company_name") for p in all_prospects}
        for comp_domain, comp_name in unique_companies.items():
            comp_name = comp_name or comp_domain
            await log_to_pipeline(run_id, "INFO", f"[Stage 3] Researching {comp_name} via Serper for context...", stage=3)
            serper_context = await search_company_context(comp_domain, comp_name)
            summary = await generate_company_summary(comp_name, serper_context, run_id)
            company_summaries[comp_domain] = summary
        
        contacts_to_review = []
        scored_count = 0
        async with get_client() as client:
            for vp in all_prospects:
                score, reason = await score_lead(vp, run_id)
                contact_id = f"cont_{uuid.uuid4()}"
                included = 1 if score >= 65 else 0
                if included:
                    scored_count += 1
                
                await client.execute(
                    "INSERT INTO contacts (id, run_id, company_id, company_domain, company_name, first_name, last_name, full_name, title, seniority, linkedin_url, email, email_verified, email_source, lead_score, score_reason, included) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [contact_id, run_id, vp["company_id"], vp["company_domain"], vp["company_name"], vp.get("first_name"), vp.get("last_name"), vp.get("full_name"), vp.get("title"), vp.get("seniority"), vp.get("linkedin_url"), vp.get("email"), 1 if vp.get("email_verified") else 0, vp.get("email_source"), score, reason, included]
                )
                
                if included:
                    contacts_to_review.append({
                        "id": contact_id,
                        "full_name": vp.get("full_name"),
                        "title": vp.get("title"),
                        "company_name": vp.get("company_name") or vp.get("company_domain"),
                        "email": vp.get("email"),
                        "score": score,
                        "reason": reason,
                        "domain": vp["company_domain"]
                    })
                    
            await client.execute(
                "UPDATE pipeline_runs SET status = 'REVIEWING', contacts_verified = ?, contacts_scored = ? WHERE id = ?",
                [len(all_prospects), scored_count, run_id]
            )
            
        # Print results to CLI user
        print("\n" + "="*50)
        print(f" PIPELINE SUMMARY (Run ID: {run_id})")
        print("="*50)
        print(f"Lookalikes Discovered: {len(companies)}")
        print(f"Prospects Sourced    : {len(all_prospects)}")
        print(f"Contacts Verified    : {len(all_prospects)}")
        print(f"Leads Scored >= 65   : {scored_count}")
        print("-"*50)
        print("TARGET LEADS:")
        for idx, c in enumerate(contacts_to_review, 1):
            safe_name = c['full_name'].encode('ascii', 'ignore').decode('ascii') if c.get('full_name') else "Unknown Name"
            print(f"{idx}. {safe_name} - {c['title']} @ {c['company_name']}")
            print(f"   Email: {c['email']} | Score: {c['score']}/100")
            print(f"   Reason: {c['reason']}")
            print("-" * 50)
            
        if not contacts_to_review:
            print("No contacts passed the lead score threshold (>=65). Execution finished.")
            async with get_client() as client:
                await client.execute(
                    "UPDATE pipeline_runs SET status = 'COMPLETE', completed_at = ?, duration_seconds = ? WHERE id = ?",
                    [datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), (datetime.datetime.utcnow() - start_time).total_seconds(), run_id]
                )
            return

        # Prompt for confirmation (run in executor since input() is blocking)
        loop = asyncio.get_event_loop()
        user_choice = await loop.run_in_executor(
            None, 
            lambda: input(f"\nProceed to send personalized outreach emails to these {len(contacts_to_review)} contacts? (y/N): ")
        )
        
        if user_choice.strip().lower() != 'y':
            print("Sending cancelled by user.")
            async with get_client() as client:
                await client.execute(
                    "UPDATE pipeline_runs SET status = 'CANCELLED', completed_at = ?, duration_seconds = ? WHERE id = ?",
                    [datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), (datetime.datetime.utcnow() - start_time).total_seconds(), run_id]
                )
            await log_to_pipeline(run_id, "WARNING", "CLI pipeline cancelled before sending.", stage=None)
            return
            
        # --- STAGE 4: Outreach Sending ---
        await log_to_pipeline(run_id, "INFO", f"[Stage 4] Commencing Outreach Sendout for {len(contacts_to_review)} contacts...", stage=4)
        
        async with get_client() as client:
            await client.execute("UPDATE pipeline_runs SET status = 'SENDING' WHERE id = ?", [run_id])
            
        sent_count = 0
        failed_count = 0
        
        for c in contacts_to_review:
            # Sourcing company info
            research = await search_company_info(c["domain"], c["company_name"])
            
            # Personalize email
            subject, body_text, body_html = await personalize_email(
                {"full_name": c["full_name"], "title": c["title"], "company_name": c["company_name"], "company_domain": c["domain"]},
                research,
                sender_name=SENDER_NAME,
                run_id=run_id
            )
            
            # Send email — sender details read from env automatically
            success, message_id, error = await send_outreach_email(
                run_id,
                c["id"],
                c["email"],
                c["full_name"],
                subject,
                body_text,
                body_html,
            )
            
            # Log to DB
            log_id = f"elog_{uuid.uuid4()}"
            sent_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            status = "SENT" if success else "FAILED"
            
            async with get_client() as client:
                await client.execute(
                    "INSERT INTO email_logs (id, run_id, contact_id, recipient_email, recipient_name, subject, body_html, body_text, status, brevo_message_id, error_message, sent_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [log_id, run_id, c["id"], c["email"], c["full_name"], subject, body_html, body_text, status, message_id, error, sent_at if success else None]
                )
                
            if success:
                sent_count += 1
            else:
                failed_count += 1
                
        # Finalize run
        completed_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        total_duration = (datetime.datetime.utcnow() - start_time).total_seconds()
        
        async with get_client() as client:
            await client.execute(
                "UPDATE pipeline_runs SET status = 'COMPLETE', completed_at = ?, duration_seconds = ?, emails_sent = ?, emails_failed = ? WHERE id = ?",
                [completed_at, total_duration, sent_count, failed_count, run_id]
            )
            
        print("\n" + "="*50)
        print(" CLI EXECUTION COMPLETE")
        print("="*50)
        print(f"Emails Sent  : {sent_count}")
        print(f"Emails Failed: {failed_count}")
        print(f"Duration     : {total_duration:.1f}s")
        print("="*50)
        
    except Exception as e:
        total_duration = (datetime.datetime.utcnow() - start_time).total_seconds()
        async with get_client() as client:
            await client.execute(
                "UPDATE pipeline_runs SET status = 'ERROR', error_message = ?, duration_seconds = ? WHERE id = ?",
                [str(e), total_duration, run_id]
            )
        print(f"\nPipeline CRASHED: {e}")

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    if len(sys.argv) < 2:
        print("Usage: python main.py <seed_domain>")
        sys.exit(1)
        
    domain = sys.argv[1].strip()
    # Strip protocols
    domain = re.sub(r'^https?://', '', domain)
    domain = re.sub(r'^www\.', '', domain)
    domain = domain.split('/')[0]
    
    if not DOMAIN_PATTERN.match(domain):
        print(f"Error: '{domain}' is not a valid domain format.")
        sys.exit(1)
        
    print(f"Starting ColdChain CLI for: {domain}")
    asyncio.run(run_cli(domain))
