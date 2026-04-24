"""Mint LiveKit participant JWTs for Squinia simulation rooms."""
from __future__ import annotations

from uuid import UUID

from app.core.config import settings
from app.core.exceptions import AppError


def livekit_room_name_for_session(session_id: UUID) -> str:
    return f"squinia-{session_id}"


def issue_livekit_participant_token(*, session_id: UUID, user_id: UUID, display_name: str) -> tuple[str, str, str]:
    """
    Returns (server_url, room_name, participant_jwt).

    Requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in settings.
    """
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise AppError(
            status_code=503,
            code="LIVEKIT_NOT_CONFIGURED",
            message="LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET.",
        )

    try:
        from livekit import api as lk_api  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise AppError(
            status_code=500,
            code="LIVEKIT_SDK_MISSING",
            message="livekit-api package is not installed.",
        ) from e

    room = livekit_room_name_for_session(session_id)
    grant = lk_api.VideoGrants(room_join=True, room=room)
    token = (
        lk_api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(str(user_id))
        .with_name(display_name[:64] or "Learner")
        .with_grants(grant)
        .to_jwt()
    )
    return settings.LIVEKIT_URL.strip(), room, token
