from fastapi import APIRouter

from secure_knowledge_api.routes.admin.answers import router as answers_router
from secure_knowledge_api.routes.admin.audit import router as audit_router
from secure_knowledge_api.routes.admin.documents import router as documents_router
from secure_knowledge_api.routes.admin.evaluations import (
    router as evaluations_router,
)
from secure_knowledge_api.routes.admin.metrics import router as metrics_router
from secure_knowledge_api.routes.admin.retrieval import router as retrieval_router

router = APIRouter()
router.include_router(answers_router)
router.include_router(audit_router)
router.include_router(documents_router)
router.include_router(evaluations_router)
router.include_router(metrics_router)
router.include_router(retrieval_router)

__all__ = ["router"]
