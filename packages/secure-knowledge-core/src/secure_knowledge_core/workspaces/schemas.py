from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from secure_knowledge_core.database.enums import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    slug: str


class WorkspaceMemberCreate(BaseModel):
    user_id: UUID
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
