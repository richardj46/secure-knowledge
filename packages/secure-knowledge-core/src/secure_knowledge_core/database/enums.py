from enum import StrEnum

from sqlalchemy import Enum


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class WorkspaceRole(StrEnum):
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class DocumentVisibility(StrEnum):
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    RESTRICTED = "restricted"
    OWNER = "owner"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    STORED = "stored"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentVersionStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentPermissionLevel(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    MANAGER = "manager"


DOCUMENT_PERMISSION_LEVEL_ENUM = Enum(
    DocumentPermissionLevel,
    name="document_permission_level",
    native_enum=True,
)
