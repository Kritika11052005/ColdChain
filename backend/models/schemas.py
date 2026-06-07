from pydantic import BaseModel, Field
from typing import Optional, List

class PipelineStartRequest(BaseModel):
    seed_domain: str

class PipelineStartResponse(BaseModel):
    run_id: str
    status: str
    websocket_url: str

class CompanySchema(BaseModel):
    id: str
    domain: str
    name: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = None

class ContactSchema(BaseModel):
    id: str
    full_name: str
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: str
    email: Optional[str] = None
    email_verified: bool = False
    lead_score: Optional[int] = None
    score_reason: Optional[str] = None
    included: bool = True

class EmailPreviewSchema(BaseModel):
    contact_id: str
    subject: str
    body_text: str
    body_html: str

class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str
    seed_domain: str
    companies_found: int
    prospects_found: int
    contacts_verified: int
    contacts_scored: int
    duration_seconds: Optional[float] = None
    emails_sent: int = 0
    emails_failed: int = 0
    error_message: Optional[str] = None

class ReviewContactsResponse(BaseModel):
    run_id: str
    total_contacts: int
    contacts: List[ContactSchema]

class SendRequest(BaseModel):
    run_id: str
    contact_ids: List[str]

class EmailResult(BaseModel):
    contact_id: str
    email: str
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None

class SendResponse(BaseModel):
    sent: int
    failed: int
    results: List[EmailResult]

class RunHistoryItem(BaseModel):
    id: str
    seed_domain: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    contacts_verified: int
    emails_sent: int

class RunLogItem(BaseModel):
    level: str
    stage: Optional[int] = None
    message: str
    timestamp: str
