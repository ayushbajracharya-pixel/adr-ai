import boto3

from app.config.settings import settings


class S3Client:
    """A singleton class to manage the S3 client connection."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Client, cls).__new__(cls)
            
            # Configure client with LocalStack endpoint if provided
            client_kwargs = {
                "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                "region_name": settings.S3_BUCKET_REGION,
            }
            
            # Add endpoint URL for LocalStack
            if settings.AWS_ENDPOINT_URL:
                client_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
            
            cls._instance.client = boto3.client("s3", **client_kwargs)
            
            # Create bucket if using LocalStack and bucket doesn't exist
            # Also ensure bucket is public for LocalStack
            if settings.AWS_ENDPOINT_URL:
                bucket_exists = False
                try:
                    cls._instance.client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
                    bucket_exists = True
                except cls._instance.client.exceptions.ClientError:
                    # Bucket doesn't exist, create it
                    cls._instance.client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                
                # Make bucket public for LocalStack (whether it existed or was just created)
                try:
                    # Disable block public access
                    cls._instance.client.delete_public_access_block(
                        Bucket=settings.S3_BUCKET_NAME
                    )
                except cls._instance.client.exceptions.ClientError:
                    pass  # May not exist, that's fine
                
                # Set bucket ACL to public-read
                try:
                    cls._instance.client.put_bucket_acl(
                        Bucket=settings.S3_BUCKET_NAME,
                        ACL="public-read"
                    )
                except cls._instance.client.exceptions.ClientError:
                    pass  # May fail, but that's okay
        return cls._instance

    def get_client(self):
        """Returns the configured S3 client."""
        return self.client
