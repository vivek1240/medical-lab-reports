from fastapi import Header, HTTPException


async def get_user_id(x_mhc_user_id: str | None = Header(default=None, alias="X-MHC-User-Id")) -> str:
    user_id = (x_mhc_user_id or "").strip()
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="User ID required")
    return user_id
