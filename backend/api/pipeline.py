import os
import uuid
import datetime
import asyncio
import re
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
from typing import List, Optional
import httpx

from models.schemas import (
    PipelineStartRequest, PipelineStartResponse,
    ReviewContactsResponse, ContactSchema,
    SendRequest, SendResponse, EmailResult
)
from models.database import get_client
from utils.logger import log_to_pipeline
from utils.deduplicator import deduplicate_contacts
from services.discovery_service import find_lookalike_companies
from services.prospeo_service import find_decision_makers
from services.gemini_service import score_lead, personalize_email, generate_company_summary
from services.serper_service import search_company_context, search_company_info
from services.brevo_service import send_outreach_email, SENDER_NAME, SENDER_EMAIL

router = APIRouter()

MAX_CONTACTS_PER_COMPANY = 5

DOMAIN_PATTERN = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\. )'
    r'+[a-zA-Z]{2,}$'.replace('. ', '.')
)

def clean_domain(v: str) -> str:
    v = v.strip().lower()
    v = re.sub(r'^https?://', '', v)
    v = re.sub(r'^www\.', '', v)
    v = v.split('/')[0]
    if not DOMAIN_PATTERN.match(v):
        raise ValueError('Invalid domain format')
    if len(v) > 253:
        raise ValueError('Domain too long')
    return v

async def verify_turnstile(token: str) -> bool:
    if token == "1x00000000000000000000AA" or os.getenv("ENVIRONMENT") == "development":
        return True
    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        return True # Skip if not configured in env
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": secret,
                    "response": token
                },
                timeout=5
            )
            return response.json().get("success", False)
    except Exception:
        return False

# Background pipeline task for Stage 1, 2, 3
async def run_pipeline_orchestrator(run_id: str, seed_domain: str):
    start_time = datetime.datetime.utcnow()
    
    try:
        await log_to_pipeline(run_id, "INFO", f"ColdChain Pipeline initiated for seed domain: {seed_domain}", stage=None)
        
        # --- STAGE 1: Dynamic AI-Powered Company Discovery (Serper + Gemini) ---
        await log_to_pipeline(run_id, "INFO", "[Stage 1] Executing Dynamic AI-Powered Company Discovery...", stage=1)
        companies = await find_lookalike_companies(seed_domain, run_id)
        
        # Empty pipeline guard
        if not companies:
            await log_to_pipeline(run_id, "ERROR", "Could not find lookalike companies for this domain. Try a more well-known company.", stage=1)
            raise Exception("Could not find lookalike companies for this domain. Try a more well-known company.")
            
        async with get_client() as client:
            # Save companies
            for comp in companies:
                comp_id = f"comp_{uuid.uuid4()}"
                comp["id"] = comp_id
                await client.execute(
                    "INSERT INTO companies (id, run_id, domain, name, industry, employee_count, country, description, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [comp_id, run_id, comp["domain"], comp.get("name"), comp.get("industry"), comp.get("employee_count"), comp.get("country"), comp.get("description"), comp.get("source", "serper_gemini")]
                )
            
            # Update run stats
            await client.execute(
                "UPDATE pipeline_runs SET companies_found = ? WHERE id = ?",
                [len(companies), run_id]
            )
            
        # --- STAGE 2: Decision Maker Discovery (Prospeo) ---
        await log_to_pipeline(run_id, "INFO", f"[Stage 2] Commencing Decision Maker Discovery via Prospeo for {len(companies)} companies...", stage=2)
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
            raise Exception("No decision-makers sourced. Pipeline stopped.")
            
        await log_to_pipeline(run_id, "SUCCESS", f"[Stage 2] Sourced {len(all_prospects)} total target prospects across companies.", stage=2)
        
        async with get_client() as client:
            await client.execute(
                "UPDATE pipeline_runs SET prospects_found = ? WHERE id = ?",
                [len(all_prospects), run_id]
            )
            
        # --- STAGE 3: AI Lead Scoring (Gemini) ---
        # Skip contacts without emails in Stage 3
        all_prospects = [p for p in all_prospects if p.get("email")]
        
        # Deduplicate contacts by email before scoring
        all_prospects = deduplicate_contacts(all_prospects)
        
        # For each company, generate a summary via Serper + Gemini
        company_summaries = {}
        unique_companies = {p.get("company_domain"): p.get("company_name") for p in all_prospects}
        for comp_domain, comp_name in unique_companies.items():
            comp_name = comp_name or comp_domain
            await log_to_pipeline(run_id, "INFO", f"[Stage 3] Researching {comp_name} via Serper for context...", stage=3)
            serper_context = await search_company_context(comp_domain, comp_name)
            summary = await generate_company_summary(comp_name, serper_context, run_id)
            company_summaries[comp_domain] = summary
        
        # Score leads
        scored_count = 0
        async with get_client() as client:
            for vp in all_prospects:
                # Score each contact
                score, reason = await score_lead(vp, run_id)
                contact_id = f"cont_{uuid.uuid4()}"
                
                # Only pass contacts scoring >= 65
                included = 1 if score >= 65 else 0
                if included:
                    scored_count += 1
                
                # Store company summary in the contact for later use
                vp["company_summary"] = company_summaries.get(vp.get("company_domain"), "")
                
                await client.execute(
                    "INSERT INTO contacts (id, run_id, company_id, company_domain, company_name, first_name, last_name, full_name, title, seniority, linkedin_url, email, email_verified, email_source, lead_score, score_reason, included) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [contact_id, run_id, vp["company_id"], vp["company_domain"], vp["company_name"], vp.get("first_name"), vp.get("last_name"), vp.get("full_name"), vp.get("title"), vp.get("seniority"), vp.get("linkedin_url"), vp.get("email"), 1 if vp.get("email_verified") else 0, vp.get("email_source"), score, reason, included]
                )
                
            # Update stats
            await client.execute(
                "UPDATE pipeline_runs SET status = 'REVIEWING', contacts_verified = ?, contacts_scored = ? WHERE id = ?",
                [len(all_prospects), scored_count, run_id]
            )
            
        duration = (datetime.datetime.utcnow() - start_time).total_seconds()
        async with get_client() as client:
            await client.execute(
                "UPDATE pipeline_runs SET duration_seconds = ? WHERE id = ?",
                [duration, run_id]
            )
            
        await log_to_pipeline(run_id, "SUCCESS", f"Pipeline completed Stages 1-3. Status: REVIEWING. Awaiting user confirmation.", stage=3)
        
    except Exception as e:
        duration = (datetime.datetime.utcnow() - start_time).total_seconds()
        async with get_client() as client:
            await client.execute(
                "UPDATE pipeline_runs SET status = 'ERROR', error_message = ?, duration_seconds = ? WHERE id = ?",
                [str(e), duration, run_id]
            )
        await log_to_pipeline(run_id, "ERROR", f"Pipeline execution failed: {e}", stage=None)

@router.post("/api/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(
    request: PipelineStartRequest,
    background_tasks: BackgroundTasks,
    x_turnstile_token: Optional[str] = Header(None, alias="X-Turnstile-Token")
):
    # Validate Domain
    try:
        clean_domain_name = clean_domain(request.seed_domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Verify Turnstile CAPTCHA
    if x_turnstile_token:
        verified = await verify_turnstile(x_turnstile_token)
        if not verified:
            raise HTTPException(status_code=403, detail="CAPTCHA verification failed")
            
    run_id = f"run_{uuid.uuid4()}"
    started_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save running pipeline in DB
    try:
        async with get_client() as client:
            await client.execute(
                "INSERT INTO pipeline_runs (id, seed_domain, status, started_at) VALUES (?, ?, ?, ?)",
                [run_id, clean_domain_name, "RUNNING", started_at]
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {e}")
        
    # Start Orchestrator Background Task
    background_tasks.add_task(run_pipeline_orchestrator, run_id, clean_domain_name)
    
    # WebSocket URL construction
    websocket_url = f"ws://localhost:8000/ws/pipeline/{run_id}"
    
    return PipelineStartResponse(
        run_id=run_id,
        status="RUNNING",
        websocket_url=websocket_url
    )

@router.get("/api/pipeline/{run_id}/contacts", response_model=ReviewContactsResponse)
async def get_pipeline_contacts(run_id: str):
    # Fetch contacts
    async with get_client() as client:
        # Check run status
        run_res = await client.execute("SELECT status FROM pipeline_runs WHERE id = ?", [run_id])
        if not run_res.rows:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
            
        contacts_res = await client.execute(
            "SELECT id, full_name, title, company_name, company_domain, email, email_verified, lead_score, score_reason, included FROM contacts WHERE run_id = ?",
            [run_id]
        )
        
        contacts = []
        for r in contacts_res.rows:
            contacts.append(ContactSchema(
                id=r[0],
                full_name=r[1],
                title=r[2],
                company_name=r[3],
                company_domain=r[4],
                email=r[5],
                email_verified=bool(r[6]),
                lead_score=r[7],
                score_reason=r[8],
                included=bool(r[9])
            ))
            
        return ReviewContactsResponse(
            run_id=run_id,
            total_contacts=len(contacts),
            contacts=contacts
        )

# Background task to send emails (Stage 4)
async def run_email_sending_stage(run_id: str, contact_ids: List[str]):
    await log_to_pipeline(run_id, "INFO", f"[Stage 4] Commencing Outreach Sendout for {len(contact_ids)} selected contacts...", stage=4)
    
    async with get_client() as client:
        # Set status to sending
        await client.execute(
            "UPDATE pipeline_runs SET status = 'SENDING' WHERE id = ?",
            [run_id]
        )
        
        # Get start time of sending
        send_start_time = datetime.datetime.utcnow()
        
        # Fetch all contacts for this run
        all_contacts_res = await client.execute(
            "SELECT id, email, full_name, title, company_domain, company_name FROM contacts WHERE run_id = ?",
            [run_id]
        )
        
        contacts_map = {row[0]: row for row in all_contacts_res.rows}
        
        # Update included flag for all contacts
        for cid in contacts_map.keys():
            included = 1 if cid in contact_ids else 0
            await client.execute(
                "UPDATE contacts SET included = ? WHERE id = ?",
                [included, cid]
            )
            
        sent_count = 0
        failed_count = 0
        
        for cid in contact_ids:
            if cid not in contacts_map:
                continue
            row = contacts_map[cid]
            email = row[1]
            name = row[2]
            title = row[3]
            domain = row[4]
            company_name = row[5] or domain
            
            # Step 1: Search Company Info (Serper)
            await log_to_pipeline(run_id, "INFO", f"[Stage 4] Sourcing context on {company_name} via Serper Search...", stage=4)
            research = await search_company_info(domain, company_name)
            
            # Step 2: Personalize Email (Gemini)
            subject, body_text, body_html = await personalize_email(
                {"full_name": name, "title": title, "company_name": company_name, "company_domain": domain},
                research,
                sender_name=SENDER_NAME,
                run_id=run_id
            )
            
            # Step 3: Send Email (Brevo) — sender details read from env automatically
            success, message_id, error = await send_outreach_email(
                run_id,
                cid,
                email,
                name,
                subject,
                body_text,
                body_html,
            )
            
            # Save email log
            log_id = f"elog_{uuid.uuid4()}"
            sent_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            status = "SENT" if success else "FAILED"
            
            await client.execute(
                "INSERT INTO email_logs (id, run_id, contact_id, recipient_email, recipient_name, subject, body_html, body_text, status, brevo_message_id, error_message, sent_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [log_id, run_id, cid, email, name, subject, body_html, body_text, status, message_id, error, sent_at if success else None]
            )
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
                
        # Fetch current duration
        run_res = await client.execute("SELECT started_at, duration_seconds FROM pipeline_runs WHERE id = ?", [run_id])
        started_at_str = run_res.rows[0][0]
        prev_duration = run_res.rows[0][1] or 0.0
        
        # Final completed values
        completed_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        started_dt = datetime.datetime.strptime(started_at_str, "%Y-%m-%d %H:%M:%S")
        total_duration = (datetime.datetime.utcnow() - started_dt).total_seconds()
        
        await client.execute(
            "UPDATE pipeline_runs SET status = 'COMPLETE', completed_at = ?, duration_seconds = ?, emails_sent = ?, emails_failed = ? WHERE id = ?",
            [completed_at, total_duration, sent_count, failed_count, run_id]
        )
        
        await log_to_pipeline(run_id, "SUCCESS", f"Pipeline RUN COMPLETE. Dispatched: {sent_count}. Failed: {failed_count}. Total Duration: {total_duration:.1f}s.", stage=None)

@router.post("/api/pipeline/{run_id}/send", response_model=SendResponse)
async def send_pipeline_emails(run_id: str, request: SendRequest, background_tasks: BackgroundTasks):
    if run_id != request.run_id:
        raise HTTPException(status_code=400, detail="Run ID mismatch")
        
    # Check if run exists and is in REVIEWING status
    async with get_client() as client:
        run_res = await client.execute("SELECT status FROM pipeline_runs WHERE id = ?", [run_id])
        if not run_res.rows:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        status = run_res.rows[0][0]
        if status != "REVIEWING":
            raise HTTPException(status_code=400, detail=f"Pipeline is not in REVIEWING state (Current state: {status})")
            
    # Trigger send out background tasks
    background_tasks.add_task(run_email_sending_stage, run_id, request.contact_ids)
    
    # We will return immediate mock results which will later update in real-time in database
    # Create the immediate results list to response
    async with get_client() as client:
        contacts_res = await client.execute(
            "SELECT id, email FROM contacts WHERE run_id = ? AND id IN ({})".format(",".join(["?"] * len(request.contact_ids))),
            [run_id] + request.contact_ids
        )
        results = []
        for r in contacts_res.rows:
            results.append(EmailResult(
                contact_id=r[0],
                email=r[1],
                success=True,
                message_id=None
            ))
            
        return SendResponse(
            sent=len(request.contact_ids),
            failed=0,
            results=results
        )
