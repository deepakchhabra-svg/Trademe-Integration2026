import os
from typing import Optional
from fastapi import Request, HTTPException, Depends

Role = str

ROLE_RANK: dict[Role, int] = {
    "listing": 10,
    "fulfillment": 20,
    "power": 80,
    "root": 100,
}

def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "y", "on")

def _role_rank(role: Optional[str]) -> int:
    if not role:
        return 0
    return ROLE_RANK.get(role.strip().lower(), 0)

def _role_from_token(token: str | None) -> Role | None:
    if not token:
        return None
    token_map: dict[str, str | None] = {
        "root": os.getenv("RETAIL_OS_ROOT_TOKEN"),
        "power": os.getenv("RETAIL_OS_POWER_TOKEN"),
        "fulfillment": os.getenv("RETAIL_OS_FULFILLMENT_TOKEN"),
        "listing": os.getenv("RETAIL_OS_LISTING_TOKEN"),
    }
    for r, t in token_map.items():
        if t and token == t:
            return r
    return None

def require_authenticated(min_role: Role = "listing"):
    def _dep(request: Request) -> Role:
        role = _role_from_token(request.headers.get("X-RetailOS-Token"))
        if not role:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized (missing/invalid X-RetailOS-Token). Configure RETAIL_OS_*_TOKEN env vars.",
            )
        if _role_rank(role) < _role_rank(min_role):
            raise HTTPException(status_code=403, detail=f"Forbidden (requires {min_role})")
        return role
    return _dep

def get_request_role(request: Request) -> Role:
    default_role = (os.getenv("RETAIL_OS_DEFAULT_ROLE") or "listing").strip().lower()
    claimed_role = (request.headers.get("X-RetailOS-Role") or default_role).strip().lower()
    supplied = request.headers.get("X-RetailOS-Token")

    token_role = _role_from_token(supplied)
    if token_role:
        return token_role

    insecure_allow_header_roles = _env_bool("RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES", default=False)

    if claimed_role not in ROLE_RANK:
        return "listing"

    if not insecure_allow_header_roles and _role_rank(claimed_role) > _role_rank("listing"):
        return "listing"

    return claimed_role

def require_role(min_role: Role):
    def _dep(role: Role = Depends(get_request_role)) -> Role:
        if _role_rank(role) < _role_rank(min_role):
            raise HTTPException(status_code=403, detail=f"Forbidden (requires {min_role})")
        return role
    return _dep
