"""Owns the lifecycle of the integrated LiveKit worker process."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class WorkerStatus:
    enabled: bool
    configured: bool
    running: bool
    pid: int | None
    exit_code: int | None


class LiveKitWorkerManager:
    def __init__(self) -> None:
        self._proc: subprocess.Popen[str] | None = None
        self._log_thread: threading.Thread | None = None

    def _is_livekit_ready(self) -> bool:
        required = (
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
            settings.OPENAI_API_KEY,
            settings.DEEPGRAM_API_KEY,
        )
        return all(bool(v) for v in required)

    def start(self) -> None:
        if not settings.LIVEKIT_WORKER_AUTOSTART:
            logger.info("LiveKit worker autostart disabled")
            return
        if settings.DEBUG and not settings.LIVEKIT_WORKER_AUTOSTART_WITH_RELOAD:
            logger.info("LiveKit worker autostart skipped in DEBUG mode")
            return
        if self._proc and self._proc.poll() is None:
            logger.info("LiveKit worker already running", pid=self._proc.pid)
            return
        if not self._is_livekit_ready():
            logger.warning("LiveKit worker not started because required configuration is missing")
            return

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        env = os.environ.copy()
        env.update(
            {
                "LIVEKIT_URL": settings.LIVEKIT_URL,
                "LIVEKIT_API_KEY": settings.LIVEKIT_API_KEY,
                "LIVEKIT_API_SECRET": settings.LIVEKIT_API_SECRET,
                "LIVEKIT_AGENT_NAME": settings.LIVEKIT_AGENT_NAME,
                "OPENAI_API_KEY": settings.OPENAI_API_KEY,
                "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
                "LOG_LEVEL": settings.LOG_LEVEL,
            }
        )
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "app.agents.livekit_voice_agent", settings.LIVEKIT_WORKER_MODE],
            cwd=str(BACKEND_ROOT),
            env=env,
            creationflags=creationflags,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._start_log_forwarder()
        logger.info("Started LiveKit worker", pid=self._proc.pid, mode=settings.LIVEKIT_WORKER_MODE)

    def _start_log_forwarder(self) -> None:
        if not self._proc or not self._proc.stdout:
            return

        def _forward() -> None:
            assert self._proc is not None
            assert self._proc.stdout is not None
            try:
                for line in self._proc.stdout:
                    message = line.rstrip()
                    if message:
                        logger.info("LiveKit worker | %s", message)
            except Exception as exc:
                logger.warning("LiveKit worker log forwarding stopped", error=str(exc))

        self._log_thread = threading.Thread(target=_forward, name="livekit-worker-log-forwarder", daemon=True)
        self._log_thread.start()

    def stop(self) -> None:
        if not self._proc:
            return
        if self._proc.poll() is None:
            logger.info("Stopping LiveKit worker", pid=self._proc.pid)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Force-killing LiveKit worker", pid=self._proc.pid)
                self._proc.kill()
                self._proc.wait(timeout=5)
        if self._proc.stdout:
            self._proc.stdout.close()
        self._log_thread = None
        self._proc = None

    def status(self) -> WorkerStatus:
        running = bool(self._proc and self._proc.poll() is None)
        pid = self._proc.pid if self._proc else None
        exit_code = None if not self._proc else self._proc.poll()
        return WorkerStatus(
            enabled=settings.LIVEKIT_WORKER_AUTOSTART,
            configured=self._is_livekit_ready(),
            running=running,
            pid=pid,
            exit_code=exit_code,
        )


livekit_worker_manager = LiveKitWorkerManager()
