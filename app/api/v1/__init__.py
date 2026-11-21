# api v1 package
from fastapi import APIRouter
from app.api.v1.endpoints.documents import router as documents_router

router = APIRouter()
router.include_router(documents_router, tags=["Documents"])

__all__ = ["router"]
