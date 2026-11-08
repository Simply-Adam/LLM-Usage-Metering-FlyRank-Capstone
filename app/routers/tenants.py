from fastapi import APIRouter, Depends

from app.dependencies import get_current_tenant


router = APIRouter(tags=["Tenant"])


@router.get("/tenant")
def get_tenant(
    tenant: dict = Depends(get_current_tenant),
):
    return {
        "id": tenant["id"],
        "name": tenant["name"],
    }