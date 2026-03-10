# AWS Lambda Deployment

## Architecture

```
Client → POST /process → API Gateway → Lambda → S3 (read image) → return timing JSON
```

Images are read from S3 (not sent in the request body) to support large files (5-10 MB) that exceed API Gateway's 6 MB payload limit. The response returns timing metrics only, not the processed images.

## Prerequisites

1. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured (`aws configure`)
2. [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
3. An S3 bucket for SAM deployment artifacts (one-time setup):
   ```bash
   aws s3 mb s3://cs4296-sam-artifacts-<your-account-id> --region us-east-1
   ```

## Deploy

From the `/aws` directory:

```bash
# Build (installs Pillow into the Lambda package)
sam build

# Deploy (first time - walks through config)
sam deploy --guided

# Subsequent deploys
sam deploy
```

During `sam deploy --guided`, set:
- Stack name: `cs4296-image-processor`
- Region: `us-east-1` (or your preferred region)
- S3 bucket for artifacts: `cs4296-sam-artifacts-<your-account-id>`
- MemorySize: `512` (change to benchmark different memory configs)

## Upload Dataset to S3

After deploying, upload the dataset images to the created bucket:

```bash
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name cs4296-image-processor \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
  --output text)

aws s3 sync ../dataset/ s3://$BUCKET/dataset/ --exclude "*.md"
```

## Invoke the API

Get the endpoint URL from deploy output, then:

```bash
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/Prod/process \
  -H "Content-Type: application/json" \
  -d '{"bucket": "cs4296-image-benchmark-<account-id>", "key": "dataset/small_1.jpg"}'
```

Example response:
```json
{
  "s3_key": "dataset/small_1.jpg",
  "lambda_request_id": "abc-123",
  "duration_seconds": 0.4521,
  "original_size_bytes": 204800,
  "original_dimensions": "1920x1080",
  "resized_output_bytes": 98304,
  "gray_output_bytes": 76800,
  "blurred_output_bytes": 210000
}
```

## Benchmarking Memory Configurations

Redeploy with different memory sizes to test performance:

```bash
sam deploy --parameter-overrides MemorySize=128
sam deploy --parameter-overrides MemorySize=512
sam deploy --parameter-overrides MemorySize=1024
```

## Teardown

```bash
sam delete --stack-name cs4296-image-processor
```
