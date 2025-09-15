import boto3

from app.config.settings import settings


class S3Client:
    """A singleton class to manage the S3 client connection."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Client, cls).__new__(cls)
            cls._instance.client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.S3_BUCKET_REGION,
            )
        return cls._instance

    def get_client(self):
        """Returns the configured S3 client."""
        return self.client
