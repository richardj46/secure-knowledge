from uuid import UUID

from fastapi import Header, HTTPException, status


def get_current_user_id(
    x_user_id: str = Header(alias="X-User-ID"),
) -> UUID:
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-User-ID header.",
        ) from exc