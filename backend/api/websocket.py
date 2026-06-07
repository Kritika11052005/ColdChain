import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.logger import register_websocket, unregister_websocket, log_to_pipeline
from models.database import get_client

router = APIRouter()

@router.websocket("/ws/pipeline/{run_id}")
async def websocket_pipeline(websocket: WebSocket, run_id: str):
    # Check if run exists in DB
    try:
        async with get_client() as client:
            res = await client.execute("SELECT id FROM pipeline_runs WHERE id = ?", [run_id])
            if not res.rows:
                await websocket.close(code=1008)
                return
    except Exception:
        await websocket.close(code=1011)  # Internal error
        return

    await websocket.accept()
    register_websocket(run_id, websocket)
    
    # Replay historical logs
    try:
        async with get_client() as client:
            logs_res = await client.execute(
                "SELECT level, stage, message, timestamp FROM run_logs WHERE run_id = ? ORDER BY id ASC",
                [run_id]
            )
            for row in logs_res.rows:
                payload = {
                    "level": row[0],
                    "stage": row[1],
                    "message": row[2],
                    "timestamp": row[3]
                }
                await websocket.send_text(json.dumps(payload))
    except Exception as e:
        print(f"Error replaying logs: {e}")

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_websocket(run_id, websocket)
    except Exception:
        unregister_websocket(run_id, websocket)
