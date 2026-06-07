import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

from utils.rate_limiter import RATE_LIMITS
from utils.logger import log_to_pipeline

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Local score simulation (sandbox fallback)
def simulate_lead_score(contact: dict) -> tuple:
    title = (contact.get("title") or "").lower()
    seniority = contact.get("seniority", "MANAGER")
    company_name = contact.get("company_name") or contact.get("company_domain")
    
    score = 60
    reasons = []
    
    if seniority == "C_SUITE":
        score += 25
        reasons.append(f"Senior decision maker holding C-level title ({contact.get('title')})")
    elif seniority == "VP":
        score += 20
        reasons.append(f"High-authority VP executive role ({contact.get('title')})")
    elif seniority in ("DIRECTOR", "HEAD"):
        score += 15
        reasons.append(f"Director/Head level position ({contact.get('title')})")
    else:
        score += 5
        reasons.append(f"Managerial operations fit ({contact.get('title')})")
        
    # Email availability boost
    if contact.get("email") and contact.get("email_verified"):
        score += 5
        reasons.append("Verified email available")
    
    # Company fit score contribution
    score += 5
    reasons.append(f"Strategic industry match for lookalikes of seed company")
    
    # Cap score at 98
    score = min(score, 98)
    reason_str = " | ".join(reasons)
    
    return score, reason_str

# Local email personalization templates (sandbox fallback)
def simulate_email_personalization(contact: dict, research: str, sender_name: str) -> tuple:
    first_name = contact.get("first_name", "there")
    title = contact.get("title", "Executive")
    company_name = contact.get("company_name") or contact.get("company_domain").split(".")[0].capitalize()
    
    # Extract recent product or keywords from research
    research_kw = "scaling up your digital initiatives"
    if "payment" in research.lower() or "pay" in research.lower():
        research_kw = "streamlining merchant transactions and developer-friendly onboarding"
    elif "marketing" in research.lower() or "campaign" in research.lower():
        research_kw = "boosting user retention and automating targeted push notifications"
    elif "analytics" in research.lower() or "data" in research.lower():
        research_kw = "improving product analytics visibility and event pipelines"
        
    subject = f"Quick question regarding {company_name}'s {title} roadmap"
    
    body_html = f"""<p>Hi {first_name},</p>
<p>I was researching {company_name} and noted your focus on <strong>{research_kw}</strong>.</p>
<p>As the {title}, I imagine keeping checkout conversions high and churn rates low are top priorities heading into next quarter.</p>
<p>We've recently helped teams similar to {company_name} build high-speed integrations that reduce engineering latency by up to 35% without breaking existing dependencies.</p>
<p>Would you be open to a brief 5-minute introductory call next Tuesday at 10 AM? If not, no worries at all.</p>
<p>Best regards,<br/>
<strong>{sender_name}</strong><br/>
ColdChain Automation</p>"""

    body_text = f"""Hi {first_name},

I was researching {company_name} and noted your focus on {research_kw}.

As the {title}, I imagine keeping checkout conversions high and churn rates low are top priorities heading into next quarter.

We've recently helped teams similar to {company_name} build high-speed integrations that reduce engineering latency by up to 35% without breaking existing dependencies.

Would you be open to a brief 5-minute introductory call next Tuesday at 10 AM? If not, no worries at all.

Best regards,
{sender_name}
ColdChain Automation"""

    return subject, body_text, body_html


async def generate_company_summary(company_name: str, serper_context: str, run_id: str) -> str:
    """
    Stage 3: Generate a 2-line company summary from Serper research using Gemini.
    Used later for email personalization in Stage 4.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Sandbox mode is disabled.")
    
    await RATE_LIMITS["gemini"].acquire("gemini")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Based on the following search results about {company_name}:
{serper_context}

Write exactly 2 concise sentences summarizing what {company_name} does, their recent products, and any notable funding or news.
Return only the 2-line summary, nothing else."""

        response = model.generate_content(prompt)
        summary = response.text.strip()
        if summary:
            await log_to_pipeline(run_id, "SUCCESS", f"[Stage 3] Generated AI company summary for {company_name}.", stage=3)
            return summary
        raise RuntimeError(f"Gemini summary generation returned empty for {company_name}")
    except Exception as e:
        await log_to_pipeline(run_id, "ERROR", f"[Stage 3] Gemini summary generation failed for {company_name}: {e}", stage=3)
        raise


async def score_lead(contact: dict, run_id: str) -> tuple:
    title = contact.get("title")
    company_name = contact.get("company_name") or contact.get("company_domain")
    
    await log_to_pipeline(run_id, "INFO", f"[Stage 3] Running AI Lead Scoring for {contact.get('full_name')}...", stage=3)
    
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Sandbox mode is disabled.")
    
    await RATE_LIMITS["gemini"].acquire("gemini")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Score the following lead on a scale of 0 to 100 based on B2B SaaS cold outreach sales relevance.
        Target profiles are C-suite and VP level executives in high growth tech/fintech.
        
        Lead Details:
        - Name: {contact.get('full_name')}
        - Title: {title}
        - Company: {company_name}
        - Seniority: {contact.get('seniority')}
        - Email Available: {"Yes - verified" if contact.get('email_verified') else "Yes - unverified" if contact.get('email') else "No"}
        
        Scoring factors:
        - Seniority level (C-suite/VP = higher scores)
        - Company size relevance for B2B outreach
        - Email availability (verified email = bonus points)
        
        Return ONLY a raw JSON in this format:
        {{"score": 85, "reason": "Short reason why"}}
        """
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean JSON if wrapped in markdown
        if "```json" in text:
            text = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL).group(1)
        elif "```" in text:
            text = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL).group(1)
            
        data = json.loads(text)
        score = int(data.get("score", 70))
        reason = data.get("reason", "Good leadership fit.")
        await log_to_pipeline(run_id, "SUCCESS", f"[Stage 3] AI Scored {contact.get('full_name')}: {score}/100", stage=3)
        return score, reason
    except Exception as e:
        await log_to_pipeline(run_id, "ERROR", f"[Stage 3] Gemini lead scoring failed for {contact.get('full_name')}: {e}", stage=3)
        raise

async def personalize_email(contact: dict, research: str, sender_name: str, run_id: str) -> tuple:
    title = contact.get("title")
    company_name = contact.get("company_name") or contact.get("company_domain")
    
    await log_to_pipeline(run_id, "INFO", f"[Stage 4] Generating AI-Personalized outreach email for {contact.get('full_name')}...", stage=4)
    
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Sandbox mode is disabled.")
    
    await RATE_LIMITS["gemini"].acquire("gemini")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are writing a hyper-personalized B2B cold email to {contact.get('full_name')}, who is the {title} at {company_name}.
        
        Use the following Google search research about {company_name}:
        {research}
        
        Write the email from '{sender_name}'.
        Ensure the tone is professional, consultative, and completely un-templated.
        Make it short (under 120 words). Include a single, low-friction call to action for a 5-minute call.
        
        Return ONLY a raw JSON in this format:
        {{
            "subject": "Unique subject line",
            "body_html": "<p>Hi Name,</p><p>Email body in HTML...</p>",
            "body_text": "Hi Name,\\n\\nEmail body in plain text..."
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```json" in text:
            text = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL).group(1)
        elif "```" in text:
            text = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL).group(1)
            
        data = json.loads(text)
        subject = data.get("subject")
        body_text = data.get("body_text")
        body_html = data.get("body_html")
        
        if subject and body_text and body_html:
            await log_to_pipeline(run_id, "SUCCESS", f"[Stage 4] AI customized email for {contact.get('full_name')}.", stage=4)
            return subject, body_text, body_html
        raise RuntimeError("Gemini generated email is missing fields.")
    except Exception as e:
        await log_to_pipeline(run_id, "ERROR", f"[Stage 4] Gemini email personalization failed: {e}", stage=4)
        raise
