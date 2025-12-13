"""S3 service for file operations."""
import os
import json
import mimetypes
from urllib.parse import quote
from typing import Optional, Dict, Any, List
from botocore.exceptions import NoCredentialsError, ClientError

from app.core.config import settings
from app.services.storage.s3_client import S3Client


class S3Service:
    """Manages the business logic for file uploads to S3."""

    def __init__(
        self,
        bucket_name: str = settings.S3_BUCKET_NAME,
        region: str = settings.S3_BUCKET_REGION,
    ):
        self.s3_client = S3Client().get_client()
        self.bucket_name = bucket_name
        self.region = region
        self._set_public_read_policy()

    def upload_file(self, file_path: str, object_name: Optional[str] = None) -> bool:
        """
        Uploads a file to a specified S3 bucket.

        Args:
            file_path: Path to the file to upload.
            object_name: S3 object name. If not specified, file_path basename is used.
            
        Returns:
            True if file was uploaded, else False.
        """
        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            print(
                f"Uploading {file_path} to S3 bucket '{self.bucket_name}' as '{object_name}'..."
            )
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            print("Upload successful.")
            return True
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found.")
            return False
        except NoCredentialsError:
            print("Error: AWS credentials not found.")
            return False
        except ClientError as e:
            print(f"Error uploading file: {e}")
            return False

    def upload_fileobj(
        self, file_obj: Any, object_name: str
    ) -> Dict[str, Any]:
        """
        Uploads a file-like object (in-memory) to S3.

        Args:
            file_obj: The file-like object to upload.
            object_name: The S3 object name.
            
        Returns:
            Dictionary with s3_uri, object_key, and public_url, or False on failure.
        """
        try:
            # Use the mimetypes library to guess the Content-Type
            mime_type, _ = mimetypes.guess_type(object_name)

            # Use a default if the type can't be guessed
            content_type = mime_type if mime_type else "application/octet-stream"

            print(
                f"Uploading file-like object to S3 bucket '{self.bucket_name}' as '{object_name}'..."
            )
            # Set ACL to public-read for LocalStack compatibility
            extra_args = {
                "ContentType": content_type,
                "ACL": "public-read"
            }
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_name,
                ExtraArgs=extra_args,
            )
            s3_uri = self.get_s3_uri(object_name)
            public_url = self._get_public_url(object_name)
            print(f"✅ Successfully uploaded '{object_name}' to {s3_uri}")
            return {
                "s3_uri": s3_uri,
                "object_key": object_name,
                "public_url": public_url,
            }
        except NoCredentialsError:
            print("Error: AWS credentials not found.")
            return False
        except ClientError as e:
            print(f"Error uploading object: {e}")
            return False

    def list_files(self) -> Optional[List[Dict[str, Any]]]:
        """
        Lists all files in the S3 bucket.
        
        Returns:
            List of dictionaries with file details, or None on error.
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)

            # Check if the bucket is empty
            if "Contents" not in response:
                return []

            files = []
            for obj in response["Contents"]:
                object_key = obj["Key"]
                public_url = self._get_public_url(object_key)

                # Exclude the "adr_uploads/" folder itself if it's listed
                if object_key.endswith("/"):
                    continue

                files.append(
                    {
                        "object_key": object_key,
                        "filename": object_key.split("/")[-1],
                        "size_bytes": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "permanent_url": public_url,
                    }
                )
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            return None

    def delete_file(self, object_key: str) -> bool:
        """
        Deletes a file from the S3 bucket.
        
        Args:
            object_key: The S3 object key to delete.
            
        Returns:
            True on success, False on failure.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            print(
                f"✅ Successfully deleted '{object_key}' from s3://{self.bucket_name}"
            )
            return True
        except ClientError as e:
            print(f"❌ Error deleting object: {e}")
            return False

    def get_s3_uri(self, object_key: str) -> str:
        """Get S3 URI for an object key."""
        return f"s3://{self.bucket_name}/{object_key}"

    def get_public_url(self, object_key: str) -> str:
        """Get public URL for an object key."""
        return self._get_public_url(object_key)

    def _set_public_read_policy(self) -> None:
        """Sets a public read bucket policy. For AWS S3."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*",
                }
            ],
        }
        try:
            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name, Policy=json.dumps(policy)
            )
            print("Bucket policy set to public read.")
        except ClientError as e:
            # Note: This will fail if the bucket is not owned by the account or if permissions are insufficient.
            print(f"❌ Error setting bucket policy: {e}")

    def _get_public_url(self, object_key: str) -> str:
        """Get public URL for an object key."""
        # Ensure the object key is URL-encoded for special characters
        encoded_object_key = quote(object_key, safe="/")

        # Use LocalStack endpoint if configured, otherwise use AWS S3 format
        if settings.AWS_ENDPOINT_URL:
            # For LocalStack, construct URL using the endpoint
            endpoint = settings.AWS_ENDPOINT_URL.rstrip('/')
            # Convert 'localstack' hostname to 'localhost' for browser access
            # This handles the case where the endpoint is http://localstack:4566
            # but browsers need http://localhost:4566
            if 'localstack' in endpoint and 'localhost' not in endpoint:
                endpoint = endpoint.replace('localstack', 'localhost')
            # LocalStack format: http://localhost:4566/bucket-name/object-key
            return f"{endpoint}/{self.bucket_name}/{encoded_object_key}"
        else:
            # AWS S3 format
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{encoded_object_key}"

