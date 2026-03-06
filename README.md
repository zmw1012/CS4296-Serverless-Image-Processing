# CS4296: Serverless Image Processing Benchmark

This repository contains the source code, dataset, and deployment configurations for our CS4296 Cloud Computing Fall 2026 project. We aim to benchmark the performance (Cold Start, Warm Execution, Concurrency) of image processing tasks on **AWS Lambda** vs. **Google Cloud Functions**.

## 👨‍💻 Team Members & Roles
* **Matthew Anthony TJOA**: AWS Lead & Benchmark Engineer
* **Yaochao YAN**: GCP Lead & Data/Cost Analyst
* **Zimeng WAN**: Core Dev & Artifact/Report Manager

## 📂 Repository Structure
* `/dataset`: Contains 9 test images of varying sizes used for benchmarking. The dataset is divided into three tiers to evaluate how payload size affects execution time:
  * **Small**: < 500 KB (Tests baseline invocation and network overhead)
  * **Medium**: 1 MB - 3 MB (Simulates standard social media image uploads)
  * **Large**: 5 MB - 10 MB (Tests CPU-intensive processing and memory limits)
* `/aws`: Will contain AWS Lambda deployment configurations (e.g., SAM or Serverless Framework).
* `/gcp`: Will contain Google Cloud Functions deployment configurations.
* `/scripts`: Will contain deployment scripts and the `benchmark.py` for concurrency testing.
* `image_processor.py`: The core Python logic for image resizing, grayscale conversion, and Gaussian blur.
* `Dockerfile`: Automated container environment for local testing and deployment consistency.
* `requirements.txt`: Python dependencies (Pillow).

## 🚀 Phase 1: Local Environment Testing
To ensure environment consistency and simplify the evaluation process, we have containerized the core logic using Docker. 

### How to run the image processor locally:
You do not need to install Python or Pillow manually. Ensure you have Docker installed, then run the following commands from the repository root:

1. **Build the Docker Image:**
   ```bash
   docker build --platform linux/amd64 -t cloud-project .
