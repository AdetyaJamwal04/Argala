import asyncio
import logging
import time
from typing import Any, Dict

from app.hardware.telemetry import get_node_telemetry
from app.queue.models import JobRecord
from app.queue.repository import queue_repo

logger = logging.getLogger(__name__)


class QueueWorker:
    """
    Asynchronous Edge Worker.
    Polls the SQLite queue, claims jobs using leases, executes capabilities,
    and updates job status atomically.
    """

    def __init__(self, worker_id: str = "edge-worker-01", poll_interval: float = 1.0):
        self.worker_id = worker_id
        self.poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Started Queue Worker [%s] (poll interval: %ss)", self.worker_id, self.poll_interval)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped Queue Worker [%s]", self.worker_id)

    async def _run_loop(self):
        from app.core.identity import lockdown_manager

        while self._running:
            try:
                # Emergency Lockdown Safety Interlock: Pause processing if quarantined
                if lockdown_manager.is_locked():
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Attempt to claim next eligible job
                job = queue_repo.claim_next_job(self.worker_id, lease_seconds=30.0)
                if job:
                    await self._process_job(job)
                else:
                    # Queue is empty or all jobs leased; wait before polling again
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in worker loop: %s", e, exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _process_job(self, job: JobRecord):
        logger.info("Processing job [%s] - Capability: %s", job.id, job.capability)
        start_time = time.time()

        try:
            result = await self._dispatch_capability(job.capability, job.payload)
            execution_time = round(time.time() - start_time, 3)
            result["_execution_time_seconds"] = execution_time

            queue_repo.complete_job(job.id, result)
            logger.info("Successfully completed job [%s] in %ss", job.id, execution_time)
        except Exception as e:
            logger.error("Failed processing job [%s]: %s", job.id, e)
            queue_repo.fail_job(job.id, str(e))

    async def _dispatch_capability(self, capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches execution to the appropriate edge service handler."""

        # 1. Telemetry Snapshot Job
        if capability == "telemetry.snapshot":
            telemetry = await get_node_telemetry()
            return {
                "capability": capability,
                "telemetry": telemetry.dict(),
            }

        # 2. Echo / Diagnostic Job
        elif capability == "system.echo":
            return {
                "capability": capability,
                "echo_payload": payload,
                "processed_by": self.worker_id,
            }

        # 3. Hardware Actuation Job (vibration, TTS voice, notification)
        elif capability == "hardware.actuate":
            from app.hardware.actuation import vibrate_phone, speak_tts, send_android_notification
            tasks = []
            if payload.get("vibrate_ms"):
                tasks.append(vibrate_phone(payload["vibrate_ms"]))
            if payload.get("speak_text"):
                tasks.append(speak_tts(payload["speak_text"]))
            if payload.get("notification_title") and payload.get("notification_content"):
                tasks.append(send_android_notification(
                    payload["notification_title"],
                    payload["notification_content"],
                ))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            return {
                "capability": capability,
                "status": "actuated",
                "processed_by": self.worker_id,
            }

        # 4. Asynchronous Outbound Vault Broker Job
        elif capability == "vault.broker":
            from app.vault.manager import vault_manager
            from app.vault.models import BrokerRequest
            broker_req = BrokerRequest(**payload)
            resp = await vault_manager.broker_http_request(broker_req)
            return {
                "capability": capability,
                "status": "brokered",
                "broker_response": resp,
                "processed_by": self.worker_id,
            }

        # 5. Intentional Failure (for testing retries and Dead-Letter Queue)
        elif capability == "test.fail":
            error_message = payload.get("error", "Intentional test failure triggered")
            raise RuntimeError(error_message)

        # Unrecognized capability
        else:
            raise NotImplementedError(f"Unsupported capability: '{capability}'")


# Global worker singleton
queue_worker = QueueWorker()
