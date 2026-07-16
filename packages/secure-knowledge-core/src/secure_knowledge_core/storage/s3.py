from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from secure_knowledge_core.core.settings import get_settings


class S3ObjectStorage:
    def __init__(self) -> None:
        settings = get_settings()

        self.bucket = settings.object_storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint_url,
            region_name=settings.object_storage_region,
            aws_access_key_id=settings.object_storage_access_key,
            aws_secret_access_key=settings.object_storage_secret_key,
        )

    def upload(
        self,
        *,
        file_object: BinaryIO,
        key: str,
        content_type: str,
    ) -> None:
        file_object.seek(0)

        self.client.upload_fileobj(
            file_object,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def download(self, *, key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"].read()

    def delete(self, *, key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    def exists(self, *, key: str) -> bool:
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]

            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False

            raise