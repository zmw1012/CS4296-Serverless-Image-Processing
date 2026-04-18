# CS4296: Serverless Image Processing Benchmark

This repository contains the source code, dataset, and deployment configurations for our CS4296 Cloud Computing project. We benchmark the performance (Cold Start, Warm Execution, Concurrency) of image processing tasks on **AWS Lambda** vs. **Google Cloud Functions (Gen 2)**.

## Team Members & Roles
* **Matthew Anthony TJOA**: AWS Lead & Benchmark Engineer
* **Yaochao YAN**: GCP Lead & Data/Cost Analyst
* **Zimeng WAN**: Core Dev & Artifact/Report Manager

## Repository Structure
* `/dataset`: 9 test images across three size tiers used for benchmarking:
  * **Small**: < 500 KB (baseline invocation and network overhead)
  * **Medium**: 1 MB - 3 MB (standard social media image uploads)
  * **Large**: 5 MB - 10 MB (CPU-intensive processing and memory limits)
* `/aws`: AWS Lambda deployment using SAM (API Gateway + Lambda + S3). See [`/aws/README.md`](aws/README.md).
* `/gcp`: Google Cloud Functions (Gen 2) deployment. See [`/gcp/README.md`](gcp/README.md).
* `/scripts`: Benchmark runner (`benchmark.py`) for cold start, warm, and concurrency testing.
* `image_processor.py`: Core Python logic for image resizing, grayscale conversion, and Gaussian blur — used for local/Docker testing.
* `Dockerfile`: Containerised local test environment (Python 3.9-slim + Pillow).
* `requirements.txt`: Python dependencies (Pillow).
* `results.csv`: Benchmark results output file.

## Image Processing Operations

Each invocation performs three operations on the input image:
1. **Resize** — scale down to 50% of original dimensions (JPEG output)
2. **Grayscale** — convert to single-channel luminance (JPEG output)
3. **Gaussian Blur** — apply blur with radius 2 (JPEG output)

The response returns timing metrics only; processed images are not stored or returned.

## Local Testing (Docker)

To run the core image processor locally without installing Python or Pillow:

1. **Build the Docker image:**
   ```bash
   docker build --platform linux/amd64 -t cloud-project .
   ```

2. **Run the container:**
   ```bash
   docker run --rm cloud-project
   ```

## Benchmarking

Results are recorded to `results.csv` with columns: `timestamp`, `platform`, `test_type`, `image_key`, `image_tier`, `run_number`, `total_latency_seconds`, `processing_seconds`, `original_size_bytes`, `original_dimensions`, `status`, `error`.

The benchmark script supports four modes:

| Mode | Description |
|------|-------------|
| `cold` | 1 request per image after 30+ minutes idle (measures cold start) |
| `warm` | 100 sequential requests per image (measures steady-state latency) |
| `concurrency` | 50, 100, and 500 simultaneous requests via asyncio |
| `all` | Runs cold → warm → concurrency in sequence |

```bash
python scripts/benchmark.py --mode all \
  --aws-url https://<api-id>.execute-api.us-east-1.amazonaws.com/Prod/process \
  --aws-bucket cs4296-image-benchmark-<account-id> \
  --gcp-url https://us-central1-<project-id>.cloudfunctions.net/process_image \
  --output results.csv
```

See [`/aws/README.md`](aws/README.md) and [`/gcp/README.md`](gcp/README.md) for how to get the URLs and bucket name after deploying each platform.
