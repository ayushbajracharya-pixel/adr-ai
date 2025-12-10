#!/bin/bash

# LocalStack Setup Script
# This script sets up AWS resources (S3 bucket, policies) in LocalStack for local development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (can be overridden by environment variables)
LOCALSTACK_ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"


S3_BUCKET_NAME="${S3_BUCKET_NAME:-adr-bucket}"

echo -e "${GREEN}🚀 LocalStack Setup Script${NC}"
echo "================================"
echo ""

# Check if LocalStack is running
echo -e "${YELLOW}Checking LocalStack connection...${NC}"
if ! curl -s "${LOCALSTACK_ENDPOINT}/_localstack/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Cannot connect to LocalStack at ${LOCALSTACK_ENDPOINT}${NC}"
    echo "   Make sure LocalStack is running: docker compose up -d localstack"
    exit 1
fi
echo -e "${GREEN}✅ LocalStack is running${NC}"
echo ""

# Check if AWS CLI is available
if command -v aws &> /dev/null; then
    USE_AWS_CLI=true
    echo -e "${GREEN}✅ Using AWS CLI${NC}"
else
    USE_AWS_CLI=false
    echo -e "${YELLOW}⚠️  AWS CLI not found, will use Python boto3${NC}"
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Error: Neither AWS CLI nor Python3 is available${NC}"
        exit 1
    fi
fi
echo ""

# Setup AWS credentials for this session
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION="${AWS_REGION}"

# Function to create S3 bucket using AWS CLI
create_bucket_aws_cli() {
    echo -e "${YELLOW}Creating S3 bucket: ${S3_BUCKET_NAME}...${NC}"
    
    # Check if bucket already exists
    if aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api head-bucket --bucket "${S3_BUCKET_NAME}" 2>/dev/null; then
        echo -e "${GREEN}✅ Bucket ${S3_BUCKET_NAME} already exists${NC}"
    else
        # Create bucket
        if aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api create-bucket \
            --bucket "${S3_BUCKET_NAME}" \
            --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}" 2>/dev/null || \
           aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api create-bucket \
            --bucket "${S3_BUCKET_NAME}" \
            --region "${AWS_REGION}"; then
            echo -e "${GREEN}✅ Created bucket: ${S3_BUCKET_NAME}${NC}"
        else
            echo -e "${RED}❌ Failed to create bucket${NC}"
            exit 1
        fi
    fi
    
    # Allow public access at the bucket level (Block Public Access must be disabled even on LocalStack
    # so that the bucket policy/ACL we set later actually takes effect).
    echo -e "${YELLOW}Disabling S3 Block Public Access on the bucket...${NC}"
    aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api put-public-access-block \
        --bucket "${S3_BUCKET_NAME}" \
        --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false >/dev/null
    aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api delete-public-access-block \
        --bucket "${S3_BUCKET_NAME}" >/dev/null 2>&1 || true
    echo -e "${GREEN}✅ Block Public Access disabled${NC}"

    # Explicit ACL so that pre-signed/object URLs work without credentials.
    echo -e "${YELLOW}Setting bucket ACL to public-read...${NC}"
    aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api put-bucket-acl \
        --bucket "${S3_BUCKET_NAME}" \
        --acl public-read >/dev/null
    echo -e "${GREEN}✅ Bucket ACL set${NC}"

    # Set bucket policy for public read access
    echo -e "${YELLOW}Setting bucket policy for public read access...${NC}"
    POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::${S3_BUCKET_NAME}/*"
        }
    ]
}
EOF
)
    
    echo "${POLICY}" | aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api put-bucket-policy \
        --bucket "${S3_BUCKET_NAME}" \
        --policy file:///dev/stdin
    
    echo -e "${GREEN}✅ Bucket policy set${NC}"
    
    # Enable CORS (optional, for web access)
    echo -e "${YELLOW}Setting CORS configuration...${NC}"
    CORS_CONFIG=$(cat <<EOF
{
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "HEAD", "PUT", "POST", "DELETE"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 3000
        }
    ]
}
EOF
)
    
    echo "${CORS_CONFIG}" | aws --endpoint-url="${LOCALSTACK_ENDPOINT}" s3api put-bucket-cors \
        --bucket "${S3_BUCKET_NAME}" \
        --cors-configuration file:///dev/stdin
    
    echo -e "${GREEN}✅ CORS configuration set${NC}"
}

# Function to create S3 bucket using Python boto3
create_bucket_python() {
    echo -e "${YELLOW}Creating S3 bucket using Python boto3: ${S3_BUCKET_NAME}...${NC}"
    
    python3 <<EOF
import boto3
import json
from botocore.exceptions import ClientError
import sys

def info(msg):
    print(msg, flush=True)

# Create S3 client
s3_client = boto3.client(
    's3',
    endpoint_url='${LOCALSTACK_ENDPOINT}',
    aws_access_key_id='${AWS_ACCESS_KEY_ID}',
    aws_secret_access_key='${AWS_SECRET_ACCESS_KEY}',
    region_name='${AWS_REGION}'
)

bucket_name = '${S3_BUCKET_NAME}'

# Check if bucket exists
try:
    s3_client.head_bucket(Bucket=bucket_name)
    print(f"✅ Bucket {bucket_name} already exists")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404':
        # Bucket doesn't exist, create it
        try:
            if '${AWS_REGION}' == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': '${AWS_REGION}'}
                )
            print(f"✅ Created bucket: {bucket_name}")
        except Exception as e:
            print(f"❌ Failed to create bucket: {e}")
            exit(1)
    else:
        print(f"❌ Error checking bucket: {e}")
        exit(1)

# Disable block public access so ACL/policy are honored
try:
    s3_client.delete_public_access_block(Bucket=bucket_name)
    info("✅ Block Public Access disabled")
except ClientError:
    info("ℹ️  No existing Block Public Access configuration to delete")

# Set bucket ACL for public read
try:
    s3_client.put_bucket_acl(Bucket=bucket_name, ACL="public-read")
    info("✅ Bucket ACL set to public-read")
except Exception as e:
    print(f"⚠️  Warning: Could not set bucket ACL: {e}")

# Set bucket policy for public read access
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
        }
    ]
}

try:
    s3_client.put_bucket_policy(
        Bucket=bucket_name,
        Policy=json.dumps(policy)
    )
    print("✅ Bucket policy set for public read access")
except Exception as e:
    print(f"⚠️  Warning: Could not set bucket policy: {e}")

# Set CORS configuration
cors_config = {
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "HEAD", "PUT", "POST", "DELETE"],
            "AllowedHeaders": ["*"],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 3000
        }
    ]
}

try:
    s3_client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration=cors_config
    )
    print("✅ CORS configuration set")
except Exception as e:
    print(f"⚠️  Warning: Could not set CORS: {e}")

print("✅ Setup complete!")
EOF
}

# Main execution
if [ "$USE_AWS_CLI" = true ]; then
    create_bucket_aws_cli
else
    create_bucket_python
fi

echo ""
echo -e "${GREEN}✅ LocalStack setup complete!${NC}"
echo ""
echo "Summary:"
echo "  - S3 Bucket: ${S3_BUCKET_NAME}"
echo "  - Region: ${AWS_REGION}"
echo "  - Endpoint: ${LOCALSTACK_ENDPOINT}"
echo "  - Public Read: Enabled"
echo "  - CORS: Enabled"
echo ""
echo "You can now use the S3 bucket in your application!"
echo "Bucket URL: ${LOCALSTACK_ENDPOINT}/${S3_BUCKET_NAME}"

