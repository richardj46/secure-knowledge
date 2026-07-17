from fastapi import FastAPI

from secure_knowledge_api.middleware.request_context import (
    RequestContextMiddleware,
)
from secure_knowledge_api.routes.admin import router as admin_router
from secure_knowledge_api.routes.answers import router as answers_router
from secure_knowledge_api.routes.auth import router as auth_router
from secure_knowledge_api.routes.documents import router as documents_router
from secure_knowledge_api.routes.evaluations import router as evaluations_router
from secure_knowledge_api.routes.groups import router as groups_router
from secure_knowledge_api.routes.organizations import (
    router as organizations_router,
)
from secure_knowledge_api.routes.retrieval import router as retrieval_router
from secure_knowledge_api.routes.workspaces import router as workspaces_router
from secure_knowledge_core.core.logging import configure_logging

configure_logging(service="api")
app = FastAPI(title="Secure-Knowledge API")
app.add_middleware(RequestContextMiddleware)

app.include_router(admin_router)
app.include_router(answers_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(evaluations_router)
app.include_router(groups_router)
app.include_router(organizations_router)
app.include_router(retrieval_router)
app.include_router(workspaces_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
