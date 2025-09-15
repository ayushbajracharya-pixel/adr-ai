from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    """

    # OpenAPI
    OPENAI_API_KEY: str

    # Localstack
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    S3_BUCKET_REGION: str

    class Config:
        env_file = ".env"  # Specifies the name of the .env file


settings = Settings()
