from fastapi import FastAPI

from secure_knowledge_api.routes.organizations import router as organizations_router

app = FastAPI(title="SecureKnowledge API")

app.include_router(organizations_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}