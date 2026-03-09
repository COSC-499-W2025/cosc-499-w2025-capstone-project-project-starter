"""Public endpoints for general visibility data."""
from fastapi import APIRouter, HTTPException
from database.user_informations import get_all_users

router = APIRouter()


def _serialize_user(user: dict) -> dict:
    def _format_dt(value):
        if value is None:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    return {
        "user_id": user.get("user_id"),
        "user_name": user.get("user_name"),
        "create_time": _format_dt(user.get("create_time")),
        "last_login_time": _format_dt(user.get("last_login_time")),
        "is_login": user.get("is_login"),
    }


@router.get("/users")
async def list_users():
    """List all registered users (no password data)."""
    try:
        users = get_all_users()
        serialized = [_serialize_user(user) for user in users]
        return {
            "success": True,
            "count": len(serialized),
            "users": serialized,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")
