import os
import json
import mimetypes
from urllib.parse import quote
from botocore.exceptions import NoCredentialsError, ClientError

from app.config.settings import settings
from .s3_client import S3Client


class UploaderService:
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

    def upload_file(self, file_path, object_name=None):
        """
        Uploads a file to a specified S3 bucket.

        :param file_path: Path to the file to upload.
        :param object_name: S3 object name. If not specified, file_path basename is used.
        :return: True if file was uploaded, else Fal # Use the mimetypes library to guess the Content-Type
            mime_type, _ = mimetypes.guess_type(object_name)

            # Use a default if the type can't be guessed
            content_type = mime_type if mime_type else 'application/octet-stream' # Use the mimetypes library to guess the Content-Type
            mime_type, _ = mimetypes.guess_type(object_name)

            # Use a default if the type can't be guessed
            content_type = mime_type if mime_type else 'application/octet-stream'se.
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

    def upload_fileobj(self, file_obj, object_name):
        """
        Uploads a file-like object (in-memory) to S3.

        :param file_obj: The file-like object to upload.
        :param object_name: The S3 object name.
        :return: True if file was jsonuploaded, else False.
        """
        try:
            # Use the mimetypes library to guess the Content-Type
            mime_type, _ = mimetypes.guess_type(object_name)

            # Use a default if the type can't be guessed
            content_type = mime_type if mime_type else "application/octet-stream"

            print(
                f"Uploading file-like object to S3 bucket '{self.bucket_name}' as '{object_name}'..."
            )
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_name,
                ExtraArgs={"ContentType": content_type},
            )
            s3_uri = f"s3://{self.bucket_name}/{object_name}"
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

    def _set_public_read_policy(self):
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

    def _get_public_url(self, object_key: str):
        # Ensure the object key is URL-encoded for special characters
        encoded_object_key = quote(object_key, safe="/")

        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{encoded_object_key}"
