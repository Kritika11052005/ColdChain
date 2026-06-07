import os
import httpx
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()

from utils.rate_limiter import RATE_LIMITS
from utils.logger import log_to_pipeline

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# Read sender details exclusively from environment variables
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME")

if not SENDER_EMAIL or not SENDER_NAME:
    raise RuntimeError(
        "SENDER_EMAIL and SENDER_NAME environment variables are required. "
        "Please set them in your .env file. Example:\n"
        "  SENDER_EMAIL=your@email.com\n"
        "  SENDER_NAME=Your Name"
    )

async def send_outreach_email(
    run_id: str,
    contact_id: str,
    recipient_email: str,
    recipient_name: str,
    subject: str,
    body_text: str,
    body_html: str,
) -> tuple:
    await RATE_LIMITS["brevo"].acquire("brevo")
    
    await log_to_pipeline(run_id, "INFO", f"[Stage 4] Firing email to {recipient_email}...", stage=4)
    
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is missing. Sandbox mode is disabled.")
        
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL
        },
        "to": [
            {
                "email": recipient_email,
                "name": recipient_name
            }
        ],
        "subject": subject,
        "htmlContent": body_html,
        "textContent": body_text
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 201:
                res_json = response.json()
                message_id = res_json.get("messageId", "msg_default_id")
                await log_to_pipeline(run_id, "SUCCESS", f"[Stage 4] Email sent successfully via Brevo to {recipient_email}. Msg ID: {message_id}", stage=4)
                return True, message_id, None
            else:
                err_msg = f"Brevo rejected send ({response.status_code}): {response.text[:150]}"
                await log_to_pipeline(run_id, "ERROR", f"[Stage 4] {err_msg}", stage=4)
                raise RuntimeError(err_msg)
    except Exception as e:
        await log_to_pipeline(run_id, "ERROR", f"[Stage 4] Brevo connection failed: {e}", stage=4)
        raise
