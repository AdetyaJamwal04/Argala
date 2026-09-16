from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_scope
from app.core.identity import Principal
from app.queue.models import JobCreate, JobListResponse, JobRecord, JobStatus
from app.queue.repository import queue_repo

router = APIRouter(prefix="/jobs", tags=["Durable Queue"])


@router.post("", response_model=JobRecord, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    job_create: JobCreate,
    response: Response,
    principal: Principal = Depends(require_scope("jobs:submit")),
) -> JobRecord:
    """
    Submits a task to the durable queue.
    Idempotent: If an idempotency_key is provided and already exists, returns the existing job (HTTP 200)
    instead of creating a duplicate (HTTP 202).
    Requires 'jobs:submit' capability.
    """
    job, is_new = queue_repo.enqueue(job_create)
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return job


@router.get("/{job_id}", response_model=JobRecord)
async def get_job(
    job_id: str,
    principal: Principal = Depends(require_scope("jobs:read")),
) -> JobRecord:
    """Retrieves the current execution status, result, or error of a queued job."""
    job = queue_repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = 50,
    job_status: Optional[JobStatus] = None,
    principal: Principal = Depends(require_scope("jobs:read")),
) -> JobListResponse:
    """Lists recent jobs with optional status filtering (PENDING, RUNNING, COMPLETED, FAILED)."""
    jobs = queue_repo.list_jobs(limit=limit, status=job_status)
    return JobListResponse(jobs=jobs, total=len(jobs))
