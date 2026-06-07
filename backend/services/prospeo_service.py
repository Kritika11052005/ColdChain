import os
import httpx
from typing import List, Optional
from utils.rate_limiter import RATE_LIMITS
from utils.logger import log_to_pipeline

PROSPEO_API_KEY = os.getenv("PROSPEO_API_KEY")

# ── Exact seniority enum values from Prospeo docs ─────────────────────────
# https://prospeo.io/api-docs/enum/seniorities
PROSPEO_SENIORITY_FILTERS = [
    "C-Suite",
    "Founder/Owner",
    "Vice President",
    "Director",
    "Head",
]

# Max contacts to enrich per company — keeps daily enrich credits safe
# 7 companies × 5 contacts = 35 enrich calls/day max (limit is 50/day)
MAX_CONTACTS_PER_COMPANY = 5


def _safe_ascii(s: str) -> str:
    if not s:
        return ""
    return s.encode("ascii", "ignore").decode("ascii")


def _extract_title(person: dict) -> str:
    """Extract job title from Prospeo person object."""
    # current_job_title is the most reliable field
    title = (
        person.get("current_job_title") or
        person.get("headline") or
        ""
    )
    # Fallback: first job in job_history where current=True
    if not title:
        for job in person.get("job_history", []):
            if job.get("current"):
                title = job.get("title", "")
                break
    return _safe_ascii(title)


def _classify_seniority(title: str) -> str:
    if not title:
        return "MANAGER"
    t = title.lower()
    if any(k in t for k in ["ceo","cto","cmo","cfo","coo","chief","founder","president","owner","partner"]):
        return "C_SUITE"
    elif "vp" in t or "vice president" in t:
        return "VP"
    elif "director" in t:
        return "DIRECTOR"
    elif "head" in t:
        return "HEAD"
    return "MANAGER"


def _extract_email(person: dict) -> Optional[str]:
    """
    Extract verified email from Prospeo enrich response.
    Email is nested inside person.email.email when revealed=True.
    """
    email_obj = person.get("email", {})
    if not email_obj:
        return None
    revealed = email_obj.get("revealed", False)
    email = email_obj.get("email", "")
    if revealed and email and "*" not in email:
        return email
    return None


async def find_decision_makers(domain: str, run_id: str) -> List[dict]:
    """
    Stage 2: Decision Maker Discovery using Prospeo Search Person + Enrich Person.

    Step 1 — POST /search-person
        Filter by company website + seniority (C-Suite, VP, Director, Head, Founder)
        Returns person objects WITH person_id but WITHOUT email.
        Credit cost: 1 credit per page of 25 results.

    Step 2 — POST /enrich-person (one call per person, capped at MAX_CONTACTS_PER_COMPANY)
        Pass person_id from Step 1.
        Returns full person data including verified email.
        Credit cost: 1 credit per email found. Free if no email found.
        Set only_verified_email=True to avoid charging for unverified emails.

    Total credit usage: 1 search + up to MAX_CONTACTS_PER_COMPANY enrich = 6 credits/domain max.
    """
    if not PROSPEO_API_KEY:
        raise RuntimeError("PROSPEO_API_KEY is missing from environment.")

    headers = {
        "X-KEY": PROSPEO_API_KEY,
        "Content-Type": "application/json",
    }

    prospects = []
    seen_emails = set()

    # ── Step 1: Search Person ──────────────────────────────────────────────
    search_payload = {
        "page": 1,
        "filters": {
            "company": {
                "websites": {
                    "include": [domain]     # root domain only e.g. "moengage.com"
                }
            },
            "person_seniority": {
                "include": PROSPEO_SENIORITY_FILTERS
            },
            "person_contact_details": {
                "email": ["VERIFIED"]       # only return people who have a verified email
            },
            "max_person_per_company": MAX_CONTACTS_PER_COMPANY
        }
    }

    await log_to_pipeline(
        run_id, "INFO",
        f"[Stage 2] Searching Prospeo for decision makers at {domain}...",
        stage=2
    )

    try:
        await RATE_LIMITS["prospeo"].acquire("prospeo")
        async with httpx.AsyncClient(timeout=20) as client:

            # ── Search request ─────────────────────────────────────────────
            search_resp = await client.post(
                "https://api.prospeo.io/search-person",
                headers=headers,
                json=search_payload,
            )

            if search_resp.status_code != 200:
                snippet = search_resp.text[:300]
                await log_to_pipeline(
                    run_id, "WARNING",
                    f"[Stage 2] Prospeo search HTTP {search_resp.status_code} for {domain}: {snippet}. Skipping.",
                    stage=2
                )
                return []

            search_data = search_resp.json()

            if search_data.get("error"):
                error_code = search_data.get("error_code", "UNKNOWN")
                filter_err = search_data.get("filter_error", "")
                if error_code == "NO_RESULTS":
                    await log_to_pipeline(run_id, "WARNING", f"[Stage 2] No results from Prospeo for {domain}.", stage=2)
                    return []
                if error_code == "INSUFFICIENT_CREDITS":
                    await log_to_pipeline(run_id, "WARNING", f"[Stage 2] Prospeo credits exhausted. Skipping {domain}.", stage=2)
                    return []
                await log_to_pipeline(
                    run_id, "WARNING",
                    f"[Stage 2] Prospeo search error for {domain}: {error_code} — {filter_err}. Skipping.",
                    stage=2
                )
                return []

            results = search_data.get("results", [])
            results = results[:5]  # Hard cap — max 5 contacts per company
            if not results:
                await log_to_pipeline(run_id, "WARNING", f"[Stage 2] Prospeo returned 0 persons for {domain}.", stage=2)
                return []

            await log_to_pipeline(
                run_id, "INFO",
                f"[Stage 2] Prospeo found {len(results)} candidates for {domain}. Enriching emails...",
                stage=2
            )

            # ── Step 2: Enrich each person to get email ────────────────────
            for result in results:
                try:
                    person_obj = result.get("person", {})
                    person_id = person_obj.get("person_id") or person_obj.get("id")

                    if not person_id:
                        await log_to_pipeline(run_id, "WARNING", f"[Stage 2] No person_id in result for {domain}. Skipping.", stage=2)
                        continue

                    first_name  = _safe_ascii(person_obj.get("first_name", "") or "")
                    last_name   = _safe_ascii(person_obj.get("last_name", "") or "")
                    full_name   = _safe_ascii(person_obj.get("full_name", "") or f"{first_name} {last_name}".strip())
                    title       = _extract_title(person_obj)
                    linkedin    = person_obj.get("linkedin_url", "") or ""

                    if not full_name:
                        continue

                    # Enrich to get email — use only_verified_email=True
                    # This means we only get charged if a verified email exists
                    await RATE_LIMITS["prospeo"].acquire("prospeo")
                    enrich_resp = await client.post(
                        "https://api.prospeo.io/enrich-person",
                        headers=headers,
                        json={
                            "only_verified_email": True,
                            "data": {
                                "person_id": person_id
                            }
                        },
                        timeout=15,
                    )

                    if enrich_resp.status_code == 200:
                        enrich_data = enrich_resp.json()

                        if enrich_data.get("error"):
                            err_code = enrich_data.get("error_code", "UNKNOWN")
                            if err_code == "NO_MATCH":
                                # Person has no verified email — skip, not charged
                                await log_to_pipeline(
                                    run_id, "INFO",
                                    f"[Stage 2] No verified email for {full_name}. Skipping.",
                                    stage=2
                                )
                            elif err_code == "INSUFFICIENT_CREDITS":
                                await log_to_pipeline(run_id, "WARNING", "[Stage 2] Prospeo enrich credits exhausted.", stage=2)
                                break  # stop enriching, return what we have
                            else:
                                await log_to_pipeline(
                                    run_id, "WARNING",
                                    f"[Stage 2] Enrich error for {full_name}: {err_code}. Skipping.",
                                    stage=2
                                )
                            continue

                        # Extract email from response
                        enriched_person = enrich_data.get("person", {})
                        email = _extract_email(enriched_person)

                        if not email:
                            await log_to_pipeline(
                                run_id, "WARNING",
                                f"[Stage 2] Enrich succeeded but email masked/missing for {full_name}. Skipping.",
                                stage=2
                            )
                            continue

                        # Deduplicate by email
                        if email.lower() in seen_emails:
                            await log_to_pipeline(run_id, "INFO", f"[Stage 2] Duplicate email {email}. Skipping.", stage=2)
                            continue
                        seen_emails.add(email.lower())

                        # Use enriched title if better
                        enriched_title = _extract_title(enriched_person) or title

                        await log_to_pipeline(
                            run_id, "SUCCESS",
                            f"[Stage 2] Got verified email for {full_name} ({enriched_title}): {email}",
                            stage=2
                        )

                        prospects.append({
                            "first_name":    first_name,
                            "last_name":     last_name,
                            "full_name":     full_name,
                            "title":         enriched_title or "Executive",
                            "seniority":     _classify_seniority(enriched_title),
                            "linkedin_url":  linkedin,
                            "email":         email,
                            "email_verified": True,
                            "email_source":  "prospeo",
                            "company_domain": domain,
                        })

                    elif enrich_resp.status_code == 429:
                        await log_to_pipeline(run_id, "WARNING", f"[Stage 2] Prospeo rate limit hit for {full_name}. Stopping enrich for {domain}.", stage=2)
                        break

                    else:
                        snippet = enrich_resp.text[:200]
                        await log_to_pipeline(
                            run_id, "WARNING",
                            f"[Stage 2] Enrich HTTP {enrich_resp.status_code} for {full_name}: {snippet}. Skipping.",
                            stage=2
                        )
                        continue

                except Exception as person_err:
                    await log_to_pipeline(
                        run_id, "WARNING",
                        f"[Stage 2] Unexpected error processing contact for {domain}: {person_err}. Skipping.",
                        stage=2
                    )
                    continue

    except Exception as e:
        await log_to_pipeline(
            run_id, "WARNING",
            f"[Stage 2] Prospeo API call failed for {domain}: {e}. Skipping domain.",
            stage=2
        )
        return []

    if prospects:
        await log_to_pipeline(
            run_id, "SUCCESS",
            f"[Stage 2] Found {len(prospects)} verified contacts for {domain}.",
            stage=2
        )
    else:
        await log_to_pipeline(
            run_id, "WARNING",
            f"[Stage 2] No verified contacts found for {domain}.",
            stage=2
        )

    return prospects
