from enum import StrEnum


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class WorkspaceRole(StrEnum):
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"