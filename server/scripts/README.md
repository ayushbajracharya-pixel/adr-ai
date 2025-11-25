# LocalStack Setup Scripts

This directory contains scripts for setting up LocalStack resources for local development.

## localstack_setup.sh

Sets up AWS resources in LocalStack, including:
- S3 bucket creation
- Bucket policies for public read access
- CORS configuration

### Usage

**From the host machine:**
```bash
cd /home/leapfrog/Desktop/ADR/adr-ai/server
./scripts/localstack_setup.sh
```

**From inside a Docker container:**
```bash
docker compose exec web bash -c "cd /app && ./scripts/localstack_setup.sh"
```

**With custom environment variables:**
```bash
S3_BUCKET_NAME=my-custom-bucket \
LOCALSTACK_ENDPOINT=http://localhost:4566 \
./scripts/localstack_setup.sh
```

### Environment Variables

- `LOCALSTACK_ENDPOINT`: LocalStack endpoint URL (default: `http://localhost:4566`)
- `AWS_REGION`: AWS region (default: `us-east-1`)
- `AWS_ACCESS_KEY_ID`: AWS access key (default: `test`)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (default: `test`)
- `S3_BUCKET_NAME`: S3 bucket name (default: `adr-bucket`)

### Requirements

- LocalStack must be running
- Either AWS CLI or Python 3 with boto3 installed

### What it does

1. Checks if LocalStack is running and accessible
2. Creates the S3 bucket if it doesn't exist
3. Sets up a bucket policy for public read access
4. Configures CORS for web access
5. Provides a summary of the setup

