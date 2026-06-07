import os
import json
import asyncio
import httpx
import re
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

from typing import List
from utils.rate_limiter import RATE_LIMITS
from utils.logger import log_to_pipeline

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Extract a clean company name from a domain
def extract_company_name(domain: str) -> str:
    name_part = domain.split(".")[0]
    # Common special casing
    special_names = {
        "clevertap": "CleverTap",
        "webengage": "WebEngage",
        "moengage": "MoEngage",
        "razorpay": "Razorpay",
        "cashfree": "Cashfree",
        "hubspot": "HubSpot",
        "salesforce": "Salesforce",
        "zoominfo": "ZoomInfo",
        "braze": "Braze",
        "leanplum": "Leanplum",
        "netcore": "Netcore",
        "insider": "Insider",
        "bigbasket": "BigBasket",
        "blinkit": "Blinkit",
    }
    return special_names.get(name_part.lower(), name_part.capitalize())


async def _serper_search(query: str) -> list:
    """Run a single Serper search and return organic results."""
    if not SERPER_API_KEY:
        return []
    
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"q": query, "num": 10}
    
    try:
        await RATE_LIMITS["serper"].acquire("serper")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                return response.json().get("organic", [])
    except Exception:
        pass
    return []


async def _extract_domains_with_gemini(company_name: str, serper_results: str, run_id: str) -> List[str]:
    """Send Serper results to Gemini to extract competitor domains."""
    if not GEMINI_API_KEY:
        return []
    
    prompt = f"""Extract 5-7 direct competitor domains of {company_name}.
Only include companies that directly compete in the same product category.
Do NOT include generic tech giants like Google, Amazon, Microsoft, IBM, LinkedIn.
Return only a JSON array of domains. Example: ["square.com", "adyen.com", "paypal.com"]

Search results about "{company_name}":
{serper_results}"""

    await RATE_LIMITS["gemini"].acquire("gemini")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean JSON if wrapped in markdown
        if "```json" in text:
            text = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL).group(1)
        elif "```" in text:
            text = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL).group(1)
        
        domains = json.loads(text)
        if isinstance(domains, list):
            # Filter out non-domain strings
            clean_domains = []
            for d in domains:
                d = d.strip().lower()
                if "." in d and " " not in d and d not in ["g2.com", "capterra.com", "linkedin.com", "google.com", "youtube.com", "twitter.com", "facebook.com"]:
                    clean_domains.append(d)
            return clean_domains
    except Exception as e:
        await log_to_pipeline(run_id, "WARNING", f"[Stage 1] Gemini extraction failed: {e}", stage=1)
    
    return []


def _make_company_dict(domain: str, source: str = "serper_gemini") -> dict:
    """Create a company dict from a domain string."""
    name_part = domain.split(".")[0]
    return {
        "domain": domain,
        "name": extract_company_name(domain),
        "industry": None,
        "employee_count": None,
        "country": None,
        "description": f"Competitor discovered via AI-powered search",
        "source": source
    }


# Generic sandbox fallback companies
def _get_sandbox_companies(seed_domain: str) -> List[dict]:
    return [
        {"domain": "hubspot.com", "name": "HubSpot", "industry": "Marketing Automation", "employee_count": 7000, "country": "United States", "description": "CRM and marketing automation platform", "source": "sandbox_fallback"},
        {"domain": "salesforce.com", "name": "Salesforce", "industry": "CRM", "employee_count": 75000, "country": "United States", "description": "Cloud-based CRM provider", "source": "sandbox_fallback"},
        {"domain": "zoominfo.com", "name": "ZoomInfo", "industry": "Information Services", "employee_count": 3500, "country": "United States", "description": "GTM intelligence platform", "source": "sandbox_fallback"},
        {"domain": "outreach.io", "name": "Outreach", "industry": "Sales Engagement", "employee_count": 1200, "country": "United States", "description": "Sales execution platform", "source": "sandbox_fallback"},
        {"domain": "instantly.ai", "name": "Instantly", "industry": "Sales Engagement", "employee_count": 400, "country": "United States", "description": "Cold email outreach and deliverability platform", "source": "sandbox_fallback"},
        {"domain": "lemlist.com", "name": "Lemlist", "industry": "Email Outreach", "employee_count": 200, "country": "France", "description": "Cold email outreach platform", "source": "sandbox_fallback"},
    ]


async def find_lookalike_companies(seed_domain: str, run_id: str) -> List[dict]:
    """
    Stage 1: Dynamic AI-Powered Company Discovery.
    Uses Serper + Gemini to find competitor domains for any seed company.
    No hardcoded data — fully dynamic.
    """
    company_name = extract_company_name(seed_domain)
    await log_to_pipeline(run_id, "INFO", f"[Stage 1] Extracted company name: {company_name} from {seed_domain}", stage=1)
    
    # Check if APIs are available
    if not SERPER_API_KEY or not GEMINI_API_KEY:
        raise RuntimeError("Serper or Gemini API key is missing. Sandbox mode is disabled.")
    
    # Run Serper searches in parallel
    await log_to_pipeline(run_id, "INFO", f"[Stage 1] Querying Serper for competitors of {company_name}...", stage=1)
    
    q1 = f"top direct competitors of {company_name} B2B SaaS"
    q2 = f"site:g2.com/compare {company_name} alternatives"
    
    results1, results2 = await asyncio.gather(
        _serper_search(q1),
        _serper_search(q2)
    )
    
    combined_results = results1 + results2
    serper_results = "\n\n".join([f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}" for r in combined_results])
    
    if not serper_results:
        raise RuntimeError(f"Serper search returned no results for competitors of {company_name}.")
    
    # Send to Gemini for extraction
    await log_to_pipeline(run_id, "INFO", f"[Stage 1] Sending search results to Gemini for competitor domain extraction...", stage=1)
    domains = await _extract_domains_with_gemini(company_name, serper_results, run_id)
    
    # Filter out the seed domain
    domains = [d for d in domains if d.lower() != seed_domain.lower()]
    
    if not domains:
        raise RuntimeError("Gemini failed to extract lookalike domains. Sandbox fallback is disabled.")
    
    # Build company dicts
    companies = []
    for domain in domains:
        comp = _make_company_dict(domain)
        companies.append(comp)
        await log_to_pipeline(run_id, "INFO", f"[Stage 1] AI discovered competitor: {domain} ({comp['name']})", stage=1)
    
    await log_to_pipeline(run_id, "SUCCESS", f"[Stage 1] Serper + Gemini discovered {len(companies)} competitor companies.", stage=1)
    return companies
