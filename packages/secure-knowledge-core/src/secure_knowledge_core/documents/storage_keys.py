from uuid import UUID


def build_storage_key(
    *,
    organization_id: UUID,
    document_id: UUID,
    version_id: UUID,
) -> str:
    return (
        f"organizations/{organization_id}/"
        f"documents/{document_id}/"
        f"versions/{version_id}/original"
    )
