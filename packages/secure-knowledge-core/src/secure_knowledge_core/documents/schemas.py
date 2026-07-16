from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from secure_knowledge_core.database.enums import (
    DocumentPermissionLevel,
    DocumentStatus,
    DocumentVersionStatus,
    DocumentVisibility,
)


class DocumentUploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    slug: str = Field(
        min_length=2,
        max_length=150,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    visibility: DocumentVisibility = DocumentVisibility.WORKSPACE


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    title: str
    slug: str
    source_filename: str
    mime_type: str
    visibility: DocumentVisibility
    status: DocumentStatus
    current_version_number: int


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version_number: int
    status: DocumentVersionStatus
    file_size_bytes: int
    page_count: int | None
    chunk_count: int | None
    failure_code: str | None
    failure_message: str | None


class DocumentUserPermissionAdd(BaseModel):
    user_id: UUID
    level: DocumentPermissionLevel = DocumentPermissionLevel.VIEWER


class DocumentGroupPermissionAdd(BaseModel):
    group_id: UUID
    level: DocumentPermissionLevel = DocumentPermissionLevel.VIEWER


class DocumentUserPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    user_id: UUID
    level: DocumentPermissionLevel


class DocumentGroupPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    group_id: UUID
    level: DocumentPermissionLevel
