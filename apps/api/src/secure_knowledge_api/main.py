from fastapi import FastAPI

from secure_knowledge_api.routes.auth import router as auth_router
from secure_knowledge_api.routes.organizations import (
    router as organizations_router,
)
from secure_knowledge_api.routes.workspaces import router as workspaces_router

app = FastAPI(title="SecureKnowledge API")

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(workspaces_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
