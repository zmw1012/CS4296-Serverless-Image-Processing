import functions_framework
import json
import time
import os
from io import BytesIO
from PIL import Image, ImageFilter
from google.cloud import storage

storage_client = storage.Client()

@functions_framework.http
def process_image(request):
    try:
        request_json = request.get_json()
        if not request_json or 'key' not in request_json:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"error": 'Request body must include "bucket" and "key"'}
                ),
            }

        key = request_json['key']
        bucket_name = os.environ.get('INPUT_BUCKET')
        
        if not bucket_name:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"error": 'The environment variable \'INPUT_BUCKET\' is not set.'}
                ),
            }

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(key)
        image_bytes = blob.download_as_bytes()

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
            "body": json.dumps({
                "gcs_key": key,
                "duration_seconds": round(duration, 4),
                "original_size_bytes": len(image_bytes),
                "original_dimensions": original_dimensions,
                "resized_output_bytes": resized_bytes,
                "gray_output_bytes": gray_bytes,
                "blurred_output_bytes": blurred_bytes
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }