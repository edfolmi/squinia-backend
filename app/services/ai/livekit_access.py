"""LiveKit token, dispatch, and room lifecycle helpers."""
from __future__ import annotations

from uuid import UUID

from app.core.config import settings
from app.core.exceptions import AppError


def livekit_room_name_for_session(session_id: UUID) -> str:
    return f"squinia-{session_id}"


def _require_livekit_base_config() -> None:
    if settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET:
        return
    raise AppError(
        status_code=503,
        code="LIVEKIT_NOT_CONFIGURED",
        message="LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET.",
    )


def _require_livekit_agent_name() -> str:
    name = (settings.LIVEKIT_AGENT_NAME or "").strip()
    if name:
        return name
    raise AppError(
        status_code=503,
        code="LIVEKIT_AGENT_NOT_CONFIGURED",
        message="Set LIVEKIT_AGENT_NAME to the running worker agent name.",
    )


def _livekit_api():
    try:
        from livekit import api as lk_api  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise AppError(
            status_code=500,
            code="LIVEKIT_SDK_MISSING",
            message="livekit-api package is not installed.",
        ) from e
    return lk_api


def issue_livekit_participant_token(*, session_id: UUID, user_id: UUID, display_name: str) -> tuple[str, str, str]:
    """
    Returns (server_url, room_name, participant_jwt).

    Requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in settings.
    """
    _require_livekit_base_config()
    lk_api = _livekit_api()

    room = livekit_room_name_for_session(session_id)
    grant = lk_api.VideoGrants(
        room_join=True,
        room=room,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    token = (
        lk_api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(str(user_id))
        .with_name(display_name[:64] or "Learner")
        .with_grants(grant)
        .to_jwt()
    )
    return settings.LIVEKIT_URL.strip(), room, token


async def dispatch_livekit_agent(session_id: UUID) -> None:
    """
    Dispatches the configured LiveKit agent to the session room.
    """
    _require_livekit_base_config()
    agent_name = _require_livekit_agent_name()
    lk_api = _livekit_api()
    room = livekit_room_name_for_session(session_id)

    api = lk_api.LiveKitAPI(
        url=settings.LIVEKIT_URL.strip(),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        await api.agent_dispatch.create_dispatch(
            lk_api.CreateAgentDispatchRequest(
                room=room,
                agent_name=agent_name,
                metadata=f'{{"session_id":"{session_id}"}}',
            ),
        )
    except Exception as e:
        msg = str(e).lower()
        if "already" in msg and "dispatch" in msg:
            return
        raise AppError(
            status_code=502,
            code="LIVEKIT_AGENT_DISPATCH_FAILED",
            message=f"Could not dispatch LiveKit agent '{agent_name}' to room '{room}': {e}",
        ) from None
    finally:
        await api.aclose()


async def close_livekit_room(session_id: UUID) -> None:
    """
    Best-effort hard close for ghost rooms after session end/abandon.
    """
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        return

    try:
        lk_api = _livekit_api()
    except Exception:
        return
    room = livekit_room_name_for_session(session_id)
    api = lk_api.LiveKitAPI(
        url=settings.LIVEKIT_URL.strip(),
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    try:
        await api.room.delete_room(lk_api.DeleteRoomRequest(room=room))
    except Exception:
        # Room may already be closed; ignore cleanup failures.
        return
    finally:
        await api.aclose()
