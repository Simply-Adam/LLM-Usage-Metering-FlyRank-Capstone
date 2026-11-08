from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.repositories.tenant_repository import find_tenant_by_key_hash
from app.security import hash_api_key


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def get_current_tenant(
    api_key: str | None = Security(api_key_header),
):
    if api_key:
        key_hash = hash_api_key(api_key)
        tenant = find_tenant_by_key_hash(key_hash)

        if tenant is not None:
            return tenant

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key.",
        headers={"WWW-Authenticate": "APIKey"},
    )