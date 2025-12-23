"""
Async Job Queue for managing long-running background tasks.
"""
import uuid
import time
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(BaseModel):
    id: str
    type: str # e.g. "simulation", "optimization"
    status: JobStatus
    progress: int = 0 # 0-100
    message: str = "Initialized"
    result: Optional[Dict[str, Any]] = None
    created_at: float
    updated_at: float

# In-memory store
_jobs: Dict[str, Job] = {}

def create_job(job_type: str) -> str:
    """Create a new job and return ID."""
    job_id = str(uuid.uuid4())
    now = time.time()
    _jobs[job_id] = Job(
        id=job_id, 
        type=job_type, 
        status=JobStatus.PENDING, 
        created_at=now, 
        updated_at=now
    )
    return job_id

def update_job(job_id: str, status: JobStatus = None, progress: int = None, message: str = None, result: Dict = None):
    """Update job state."""
    if job_id not in _jobs:
        return
        
    job = _jobs[job_id]
    if status:
        job.status = status
    if progress is not None:
        job.progress = progress
    if message:
        job.message = message
    if result:
        job.result = result
        
    job.updated_at = time.time()

def get_job(job_id: str) -> Optional[Job]:
    """Retrieve job details."""
    return _jobs.get(job_id)

def list_jobs(limit: int = 10) -> list[Job]:
    """List recent jobs."""
    # Sort by updated_at desc
    sorted_jobs = sorted(_jobs.values(), key=lambda x: x.updated_at, reverse=True)
    return sorted_jobs[:limit]

def clear_jobs():
    """Clear all jobs."""
    _jobs.clear()
