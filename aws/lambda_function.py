import json
import time
import boto3
from io import BytesIO
from PIL import Image, ImageFilter

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        bucket = body.get("bucket")
        key = body.get("key")

        if not bucket or not key:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"error": 'Request body must include "bucket" and "key"'}
                ),
            }

        # Download image from S3
        s3_response = s3_client.get_object(Bucket=bucket, Key=key)
        image_bytes = s3_response["Body"].read()

        start_time = time.time()

        with Image.open(BytesIO(image_bytes)) as img:
            original_dimensions = f"{img.width}x{img.height}"

            # 1. Resize to 50%
            resized = img.resize((img.width // 2, img.height // 2))
            buf = BytesIO()
            resized.save(buf, format="JPEG")
            resized_bytes = buf.tell()

            # 2. Grayscale
            gray = img.convert("L")
            buf = BytesIO()
            gray.save(buf, format="JPEG")
            gray_bytes = buf.tell()

            # 3. Gaussian Blur
            blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
            buf = BytesIO()
            blurred.save(buf, format="JPEG")
            blurred_bytes = buf.tell()

        duration = time.time() - start_time

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "s3_key": key,
                    "lambda_request_id": context.aws_request_id,
                    "duration_seconds": round(duration, 4),
                    "original_size_bytes": len(image_bytes),
                    "original_dimensions": original_dimensions,
                    "resized_output_bytes": resized_bytes,
                    "gray_output_bytes": gray_bytes,
                    "blurred_output_bytes": blurred_bytes,
                }
            ),
        }

    except s3_client.exceptions.NoSuchKey:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Object not found in S3: {key}"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
