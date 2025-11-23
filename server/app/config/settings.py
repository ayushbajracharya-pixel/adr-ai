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

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    SECRET_KEY: str  # Secret key for session signing (generate a random string)
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend URL for OAuth redirect

    class Config:
        env_file = ".env"  # Specifies the name of the .env file


settings = Settings()
