import boto3
from botocore.exceptions import ClientError

from secure_knowledge_core.core.settings import get_settings


def main() -> None:
    settings = get_settings()

    client = boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint_url,
        region_name=settings.object_storage_region,
        aws_access_key_id=settings.object_storage_access_key,
        aws_secret_access_key=settings.object_storage_secret_key,
    )

    try:
        client.head_bucket(Bucket=settings.object_storage_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.object_storage_bucket)


if __name__ == "__main__":
    main()