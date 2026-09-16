import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.db.database import db_session
from app.queue.models import JobCreate, JobRecord, JobStatus

logger = logging.getLogger(__name__)


def _row_to_job(row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        idempotency_key=row["idempotency_key"],
        capability=row["capability"],
        payload=json.loads(row["payload"]) if row["payload"] else {},
        status=JobStatus(row["status"]),
        result=json.loads(row["result"]) if row["result"] else None,
        error=row["error"],
        retry_count=row["retry_count"],
        max_retries=row["max_retries"],
        worker_id=row["worker_id"],
        lease_expires_at=row["lease_expires_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


class QueueRepository:
    """
    Atomic SQLite Queue Operations.
    Implements Idempotency, Lease Claiming, and Dead-Letter Queueing.
    """

    def enqueue(self, job_create: JobCreate) -> Tuple[JobRecord, bool]:
        """
        Enqueues a new job.
        If an idempotency_key is provided and already exists, returns the existing job
        without creating a duplicate (is_new = False).
        """
        now = time.time()

        with db_session() as conn:
            cursor = conn.cursor()

            # Check for existing idempotency key
            if job_create.idempotency_key:
                cursor.execute(
                    "SELECT * FROM jobs WHERE idempotency_key = ?;",
                    (job_create.idempotency_key,),
                )
                existing = cursor.fetchone()
                if existing:
                    logger.info("Idempotent hit for key: %s -> returning job: %s", job_create.idempotency_key, existing["id"])
                    return _row_to_job(existing), False

            job_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO jobs (
                    id, idempotency_key, capability, payload, status,
                    max_retries, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    job_id,
                    job_create.idempotency_key,
                    job_create.capability,
                    json.dumps(job_create.payload),
                    JobStatus.PENDING.value,
                    job_create.max_retries,
                    now,
                    now,
                ),
            )
            cursor.close()

        new_job = JobRecord(
            id=job_id,
            idempotency_key=job_create.idempotency_key,
            capability=job_create.capability,
            payload=job_create.payload,
            status=JobStatus.PENDING,
            max_retries=job_create.max_retries,
            created_at=now,
            updated_at=now,
        )
        logger.info("Enqueued new job [%s] for capability: %s", job_id, job_create.capability)
        return new_job, True

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?;", (job_id,))
            row = cursor.fetchone()
            cursor.close()
            return _row_to_job(row) if row else None

    def list_jobs(self, limit: int = 50, status: Optional[JobStatus] = None) -> List[JobRecord]:
        with db_session() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?;",
                    (status.value, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?;",
                    (limit,),
                )
            rows = cursor.fetchall()
            cursor.close()
            return [_row_to_job(r) for r in rows]

    def claim_next_job(self, worker_id: str, lease_seconds: float = 30.0) -> Optional[JobRecord]:
        """
        Atomically claims the next pending or expired-lease job.
        Ensures race-condition-free single worker assignment.
        """
        now = time.time()
        lease_expiry = now + lease_seconds

        with db_session() as conn:
            cursor = conn.cursor()

            # Find next eligible job: either PENDING or RUNNING with an expired lease
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'PENDING'
                   OR (status = 'RUNNING' AND lease_expires_at < ?)
                ORDER BY created_at ASC
                LIMIT 1;
                """,
                (now,),
            )
            candidate = cursor.fetchone()
            if not candidate:
                cursor.close()
                return None

            job = _row_to_job(candidate)
            job.status = JobStatus.RUNNING
            job.worker_id = worker_id
            job.lease_expires_at = lease_expiry
            job.updated_at = now

            # Atomically acquire lease
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'RUNNING',
                    worker_id = ?,
                    lease_expires_at = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (worker_id, lease_expiry, now, job.id),
            )
            cursor.close()

        logger.info("Worker [%s] claimed lease on job [%s] until %s", worker_id, job.id, lease_expiry)
        return job

    def complete_job(self, job_id: str, result: Dict[str, Any]) -> bool:
        """Marks a job as COMPLETED with its execution output."""
        now = time.time()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = 'COMPLETED',
                    result = ?,
                    error = NULL,
                    lease_expires_at = NULL,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (json.dumps(result), now, now, job_id),
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated

    def fail_job(self, job_id: str, error_message: str) -> bool:
        """
        Handles job failure with Dead-Letter Queueing.
        If retry_count < max_retries, requeues as PENDING.
        If retries exhausted, marks as FAILED (DLQ).
        """
        now = time.time()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT retry_count, max_retries FROM jobs WHERE id = ?;", (job_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return False

            new_retry_count = row["retry_count"] + 1
            max_retries = row["max_retries"]

            if new_retry_count < max_retries:
                # Re-queue for retry
                new_status = JobStatus.PENDING.value
                logger.warning("Job [%s] failed (attempt %s/%s) -> Requeuing: %s", job_id, new_retry_count, max_retries, error_message)
            else:
                # Poison pill / Max retries exhausted -> Move to Dead-Letter Queue
                new_status = JobStatus.FAILED.value
                logger.error("Job [%s] exhausted all %s retries -> Moved to Dead-Letter Queue: %s", job_id, max_retries, error_message)

            cursor.execute(
                """
                UPDATE jobs
                SET status = ?,
                    retry_count = ?,
                    error = ?,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE id = ?;
                """,
                (new_status, new_retry_count, error_message, now, job_id),
            )
            updated = cursor.rowcount > 0
            cursor.close()
            return updated


# Global Queue Repository singleton
queue_repo = QueueRepository()
