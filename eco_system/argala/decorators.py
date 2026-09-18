"""
Cyber-Physical decorators for gating sensitive Python operations behind Argala physical approval.
"""

import functools
import logging
from typing import Any, Callable, Optional

from argala.client import ArgalaClient

logger = logging.getLogger(__name__)


def requires_approval(
    action: Optional[str] = None,
    risk_level: str = "high",
    prompt: Optional[str] = None,
    timeout_seconds: int = 60,
    client: Optional[ArgalaClient] = None,
    on_wait: Optional[Callable[[str], None]] = None,
):
    """
    Decorator that gates a Python function behind cyber-physical Human-in-the-Loop (HITL) authorization.

    When the decorated function is called:
    1. A cryptographic ticket is generated and dispatched to the Android phone.
    2. The physical phone vibrates, plays a voice announcement, and shows the approval card.
    3. The execution thread pauses and polls for human resolution.
    4. If approved: the function proceeds and returns its value.
    5. If rejected: raises ArgalaApprovalDeniedError.
    6. If timed out: raises ArgalaTimeoutError.

    Example:
        @requires_approval(action="database.drop_schema", risk_level="critical")
        def drop_database(target_cluster: str):
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            c = client or ArgalaClient()
            effective_action = action or func.__name__
            
            # Determine target representation
            if "target" in kwargs:
                effective_target = str(kwargs["target"])
            elif args:
                effective_target = str(args[0])
            else:
                effective_target = "system_resource"

            effective_prompt = prompt or f"Confirm execution of function '{func.__name__}' on '{effective_target}'"

            ticket = c.request_approval(
                action=effective_action,
                target=effective_target,
                risk_level=risk_level,
                prompt=effective_prompt,
                timeout_seconds=timeout_seconds,
            )

            if on_wait:
                on_wait(ticket.id)
            else:
                print(f"[Argala HITL Gate] Physical approval required for '{effective_action}' [Ticket {ticket.id[:8]}...]")
                print(f"[Argala HITL Gate] Check phone screen at {c.endpoint}/approvals/ui to approve...")

            # Wait for human resolution
            resolved = c.wait_for_approval(ticket.id, timeout=float(timeout_seconds + 5))
            logger.info("Function '%s' approved with token: %s", func.__name__, resolved.token)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
