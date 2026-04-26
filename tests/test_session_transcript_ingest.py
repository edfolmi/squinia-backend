from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import AppError
from app.models.auth.membership import OrgRole
from app.models.simulation.message import MessageRole
from app.models.simulation.simulation_session import SessionMode, SessionStatus
from app.schemas.simulation.requests import SimulationSessionTranscriptIngestRequest
from app.services.simulation.session import SessionService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeSessions:
    def __init__(self, row) -> None:
        self.row = row
        self.updated: dict | None = None

    async def get(self, session_id, tenant_id):
        if self.row.id == session_id and self.row.tenant_id == tenant_id:
            return self.row
        return None

    async def update(self, session_id, tenant_id, values: dict):
        self.updated = values
        for key, value in values.items():
            setattr(self.row, key, value)
        return self.row


class FakeMessages:
    def __init__(self) -> None:
        self.created: list[dict] = []

    async def list_for_session(self, session_id):
        return []

    async def get_max_turn(self, session_id):
        return 0

    async def create(self, values: dict):
        self.created.append(values)
        return SimpleNamespace(**values)


def make_service(row):
    db = FakeDb()
    service = SessionService(db)  # type: ignore[arg-type]
    service.sessions = FakeSessions(row)  # type: ignore[assignment]
    service.messages = FakeMessages()  # type: ignore[assignment]
    return service, db


def make_row(*, status: SessionStatus, mode: SessionMode):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        status=status,
        mode=mode,
        turn_count=0,
    )


@pytest.mark.asyncio
async def test_ingest_live_transcript_accepts_late_final_chunks_after_completion() -> None:
    row = make_row(status=SessionStatus.COMPLETED, mode=SessionMode.VIDEO)
    service, db = make_service(row)
    body = SimulationSessionTranscriptIngestRequest(
        items=[
            {
                "role": "USER",
                "text": "I will send the production update before end of day.",
                "segment_id": "segment-1",
                "is_final": True,
            }
        ]
    )

    result = await service.ingest_live_transcript(
        row.tenant_id,
        row.id,
        row.user_id,
        OrgRole.STUDENT,
        body,
    )

    assert result["accepted"] == 1
    assert result["turn_count"] == 1
    assert db.committed is True
    assert service.messages.created[0]["role"] == MessageRole.USER
    assert service.messages.created[0]["content_type"] == "transcript"


@pytest.mark.asyncio
async def test_ingest_live_transcript_rejects_abandoned_sessions() -> None:
    row = make_row(status=SessionStatus.ABANDONED, mode=SessionMode.VOICE)
    service, _ = make_service(row)
    body = SimulationSessionTranscriptIngestRequest(
        items=[{"role": "USER", "text": "Late abandoned text.", "is_final": True}]
    )

    with pytest.raises(AppError) as exc:
        await service.ingest_live_transcript(
            row.tenant_id,
            row.id,
            row.user_id,
            OrgRole.STUDENT,
            body,
        )

    assert exc.value.status_code == 400
    assert exc.value.code == "SESSION_ENDED"
