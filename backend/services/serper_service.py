import os
import httpx
from dotenv import load_dotenv
load_dotenv()

from utils.rate_limiter import RATE_LIMITS

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


async def search_company_context(company_domain: str, company_name: str) -> str:
    """
    Stage 3: Search for company context to feed into Gemini for summary generation.
    Query: "{company name} product funding news 2024"
    """
    if not SERPER_API_KEY:
        return f"Mock company profile: {company_name} is a leading digital services provider specializing in business operations, payment infrastructure, and software scalability."
        
    await RATE_LIMITS["serper"].acquire("serper")
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    query = f"{company_name} product funding news 2024"
    data = {
        "q": query,
        "num": 5
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=8)
            if response.status_code == 200:
                results = response.json()
                snippets = []
                for item in results.get("organic", []):
                    snippets.append(f"- {item.get('title')}: {item.get('snippet')}")
                return "\n".join(snippets)
    except Exception:
        pass
        
    return f"Default context: {company_name} ({company_domain}) is an enterprise operating in technology-enabled services and regional market solutions."


async def search_company_info(company_domain: str, company_name: str) -> str:
    """
    Stage 4: Search for company info to feed into Gemini for email personalization.
    """
    if not SERPER_API_KEY:
        return f"Mock company profile: {company_name} is a leading digital services provider specializing in business operations, payment infrastructure, and software scalability."
        
    await RATE_LIMITS["serper"].acquire("serper")
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    # Search for company background and recent milestones
    query = f"{company_name} ({company_domain}) recent milestones products news"
    data = {
        "q": query,
        "num": 3
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=8)
            if response.status_code == 200:
                results = response.json()
                snippets = []
                # Combine organic search snippets
                for item in results.get("organic", []):
                    snippets.append(f"- {item.get('title')}: {item.get('snippet')}")
                return "\n".join(snippets)
    except Exception:
        pass
        
    return f"Default context: {company_name} ({company_domain}) is an enterprise operating in technology-enabled services and regional market solutions."
