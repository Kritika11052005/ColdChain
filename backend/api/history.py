from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import RunHistoryItem, RunLogItem, PipelineStatusResponse
from models.database import get_client

router = APIRouter()

@router.get("/api/history", response_model=List[RunHistoryItem])
async def get_history():
    async with get_client() as client:
        res = await client.execute(
            "SELECT id, seed_domain, status, started_at, completed_at, duration_seconds, contacts_verified, emails_sent FROM pipeline_runs ORDER BY started_at DESC"
        )
        history = []
        for r in res.rows:
            history.append(RunHistoryItem(
                id=r[0],
                seed_domain=r[1],
                status=r[2],
                started_at=r[3],
                completed_at=r[4],
                duration_seconds=r[5],
                contacts_verified=r[6] or 0,
                emails_sent=r[7] or 0
            ))
        return history

@router.get("/api/history/{run_id}/logs", response_model=List[RunLogItem])
async def get_run_logs(run_id: str):
    async with get_client() as client:
        # Check if run exists
        run_check = await client.execute("SELECT id FROM pipeline_runs WHERE id = ?", [run_id])
        if not run_check.rows:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
            
        res = await client.execute(
            "SELECT level, stage, message, timestamp FROM run_logs WHERE run_id = ? ORDER BY id ASC",
            [run_id]
        )
        logs = []
        for r in res.rows:
            logs.append(RunLogItem(
                level=r[0],
                stage=r[1],
                message=r[2],
                timestamp=r[3]
            ))
        return logs

@router.get("/api/history/{run_id}/stats", response_model=PipelineStatusResponse)
async def get_run_stats(run_id: str):
    async with get_client() as client:
        res = await client.execute(
            "SELECT id, status, seed_domain, companies_found, prospects_found, contacts_verified, contacts_scored, duration_seconds, emails_sent, emails_failed, error_message FROM pipeline_runs WHERE id = ?",
            [run_id]
        )
        if not res.rows:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
            
        r = res.rows[0]
        return PipelineStatusResponse(
            run_id=r[0],
            status=r[1],
            seed_domain=r[2],
            companies_found=r[3] or 0,
            prospects_found=r[4] or 0,
            contacts_verified=r[5] or 0,
            contacts_scored=r[6] or 0,
            duration_seconds=r[7],
            emails_sent=r[8] or 0,
            emails_failed=r[9] or 0,
            error_message=r[10]
        )
