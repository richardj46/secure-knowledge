from enum import StrEnum

from sqlalchemy import Enum


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EVALUATION_ADMIN = "evaluation_admin"
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


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Answerability(StrEnum):
    ANSWERABLE = "answerable"
    PARTIALLY_ANSWERABLE = "partially_answerable"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


class AnswerGenerationStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationCaseStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class HumanReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ExecutionMode(StrEnum):
    PRODUCTION = "production"
    EVALUATION = "evaluation"
    TEST = "test"


DOCUMENT_PERMISSION_LEVEL_ENUM = Enum(
    DocumentPermissionLevel,
    name="document_permission_level",
    native_enum=True,
)

MESSAGE_ROLE_ENUM = Enum(
    MessageRole,
    name="message_role",
    native_enum=True,
)

ANSWERABILITY_ENUM = Enum(
    Answerability,
    name="answerability",
    native_enum=True,
)

ANSWER_GENERATION_STATUS_ENUM = Enum(
    AnswerGenerationStatus,
    name="answer_generation_status",
    native_enum=True,
)

EVALUATION_RUN_STATUS_ENUM = Enum(
    EvaluationRunStatus,
    name="evaluation_run_status",
    native_enum=True,
)

EVALUATION_CASE_STATUS_ENUM = Enum(
    EvaluationCaseStatus,
    name="evaluation_case_status",
    native_enum=True,
)

HUMAN_REVIEW_STATUS_ENUM = Enum(
    HumanReviewStatus,
    name="human_review_status",
    native_enum=True,
)

EXECUTION_MODE_ENUM = Enum(
    ExecutionMode,
    name="execution_mode",
    native_enum=True,
)
