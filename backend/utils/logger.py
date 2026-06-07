import re
import asyncio
import datetime
from typing import Dict, Set
from fastapi import WebSocket
from models.database import get_client

# Active WebSocket connections per run_id
active_websockets: Dict[str, Set[WebSocket]] = {}

def register_websocket(run_id: str, websocket: WebSocket):
    if run_id not in active_websockets:
        active_websockets[run_id] = set()
    active_websockets[run_id].add(websocket)

def unregister_websocket(run_id: str, websocket: WebSocket):
    if run_id in active_websockets:
        active_websockets[run_id].discard(websocket)
        if not active_websockets[run_id]:
            del active_websockets[run_id]

# Sensitive credentials scrubber
SENSITIVE_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+'),
    re.compile(r'xkeysib-[a-zA-Z0-9-]+'),
    re.compile(r'AIza[a-zA-Z0-9_-]{35}'),
]

def scrub_sensitive(message: str) -> str:
    for pattern in SENSITIVE_PATTERNS:
        message = pattern.sub('[REDACTED]', message)
    return message

async def log_to_pipeline(run_id: str, level: str, message: str, stage: int = None):
    # Scrub message
    scrubbed_message = scrub_sensitive(message)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Print to console
    # Add colors for console
    color_code = ""
    reset_code = "\033[0m"
    if level == "SUCCESS":
        color_code = "\033[92m" # Green
    elif level == "WARNING":
        color_code = "\033[93m" # Yellow
    elif level == "ERROR":
        color_code = "\033[91m" # Red
    elif level == "INFO":
        color_code = "\033[94m" # Blue
        
    try:
        print(f"[{timestamp}] [{level}] {color_code}{scrubbed_message}{reset_code}")
    except UnicodeEncodeError:
        safe_msg = scrubbed_message.encode('ascii', 'ignore').decode('ascii')
        print(f"[{timestamp}] [{level}] {color_code}{safe_msg}{reset_code}")
    
    # 2. Write to DB
    try:
        async with get_client() as client:
            await client.execute(
                "INSERT INTO run_logs (run_id, level, stage, message) VALUES (?, ?, ?, ?)",
                [run_id, level, stage, scrubbed_message]
            )
    except Exception as e:
        print(f"Failed to log to database: {e}")

    # 3. Broadcast to websockets
    if run_id in active_websockets:
        payload = {
            "timestamp": timestamp,
            "level": level,
            "stage": stage,
            "message": scrubbed_message
        }
        # Schedule sending to prevent blocking the main pipeline flow
        asyncio.create_task(broadcast_log(run_id, payload))

async def broadcast_log(run_id: str, payload: dict):
    if run_id not in active_websockets:
        return
    
    import json
    websockets_copy = list(active_websockets[run_id])
    for ws in websockets_copy:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            # Safe to discard dead sockets
            active_websockets[run_id].discard(ws)
