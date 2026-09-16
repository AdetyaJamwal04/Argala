import asyncio
import json
import logging
import os
import shutil
import time
from typing import Optional
# pyrefly: ignore [missing-import] 
from pydantic import BaseModel, Field 

from app.config import settings

logger = logging.getLogger(__name__)


class BatteryInfo(BaseModel):
    percentage: int = 100
    plugged: str = "UNKNOWN"
    status: str = "UNKNOWN"
    temperature: float = 0.0
    health: str = "GOOD"
    source: str = "mock"


class MemoryInfo(BaseModel):
    total_mb: int = 0
    available_mb: int = 0
    used_mb: int = 0
    usage_percent: float = 0.0


class NodeTelemetry(BaseModel):
    node_id: str
    gateway_name: str
    is_android: bool
    uptime_seconds: float
    timestamp: float = Field(default_factory=time.time)
    battery: BatteryInfo
    memory: MemoryInfo


START_TIME = time.time()


async def get_battery_telemetry() -> BatteryInfo:
    """
    Non-blocking async query to termux-battery-status.
    Uses a 2-second timeout to prevent Android sensor hangs from starving the event loop.
    """
    # Check if termux-battery-status is in PATH
    binary_path = shutil.which("termux-battery-status")
    if not binary_path:
        return BatteryInfo(source="unavailable (not in Termux or termux-api missing)")

    try:
        proc = await asyncio.create_subprocess_exec(
            binary_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=2.0)

        if proc.returncode == 0 and stdout:
            data = json.loads(stdout.decode("utf-8"))
            return BatteryInfo(
                percentage=int(data.get("percentage", 100)),
                plugged=str(data.get("plugged", "UNPLUGGED")),
                status=str(data.get("status", "DISCHARGING")),
                temperature=float(data.get("temperature", 0.0)),
                health=str(data.get("health", "GOOD")),
                source="termux-api",
            )
        else:
            logger.warning("termux-battery-status returned non-zero: %s", stderr.decode("utf-8", errors="ignore"))
    except asyncio.TimeoutError:
        logger.warning("Timeout querying termux-battery-status (2.0s exceeded)")
    except Exception as e:
        logger.warning("Failed to query battery status: %s", e)

    return BatteryInfo(source="error_fallback")


async def get_memory_telemetry() -> MemoryInfo:
    """
    Reads Linux/Android memory usage directly from /proc/meminfo.
    Extremely fast and avoids external binary dependencies.
    """
    meminfo_path = "/proc/meminfo"
    if not os.path.exists(meminfo_path):
        # Running on Windows or non-Linux host
        return MemoryInfo(total_mb=4096, available_mb=2048, used_mb=2048, usage_percent=50.0)

    try:
        mem_data = {}
        with open(meminfo_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]  # kB value
                    mem_data[key] = int(val)

        total_kb = mem_data.get("MemTotal", 0)
        avail_kb = mem_data.get("MemAvailable", mem_data.get("MemFree", 0))
        used_kb = max(0, total_kb - avail_kb)

        total_mb = total_kb // 1024
        avail_mb = avail_kb // 1024
        used_mb = used_kb // 1024
        usage_pct = round((used_kb / total_kb * 100.0), 1) if total_kb > 0 else 0.0

        return MemoryInfo(
            total_mb=total_mb,
            available_mb=avail_mb,
            used_mb=used_mb,
            usage_percent=usage_pct,
        )
    except Exception as e:
        logger.warning("Failed to parse /proc/meminfo: %s", e)
        return MemoryInfo()


async def get_node_telemetry() -> NodeTelemetry:
    """
    Aggregates comprehensive hardware and system telemetry for the control plane.
    """
    is_android = os.path.exists("/data/data/com.termux")
    battery_task = asyncio.create_task(get_battery_telemetry())
    memory_task = asyncio.create_task(get_memory_telemetry())

    battery, memory = await asyncio.gather(battery_task, memory_task)

    return NodeTelemetry(
        node_id=settings.NODE_ID,
        gateway_name=settings.GATEWAY_NAME,
        is_android=is_android,
        uptime_seconds=round(time.time() - START_TIME, 2),
        battery=battery,
        memory=memory,
    )
