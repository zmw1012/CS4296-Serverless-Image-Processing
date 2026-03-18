#!/usr/bin/env python3
"""
benchmark.py - Benchmark AWS Lambda and GCP Cloud Functions for image processing.

Usage:
    python benchmark.py \
        --aws-url <API_GATEWAY_URL> \
        --aws-bucket <S3_BUCKET_NAME> \
        [--gcp-url <GCP_URL>] \
        [--runs 5] \
        [--concurrency 10] \
        [--output results.csv]

Example:
    python benchmark.py \
        --aws-url https://abc123.execute-api.us-east-1.amazonaws.com/Prod/process \
        --aws-bucket cs4296-image-benchmark-123456789012 \
        --runs 5 \
        --output results.csv
"""

import argparse
import csv
import json
import time
import statistics
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# The 9 benchmark images grouped by tier
IMAGES = [
    ("small",  "dataset/small_1.jpg"),
    ("small",  "dataset/small_2.jpg"),
    ("small",  "dataset/small_3.jpg"),
    ("medium", "dataset/medium_1.jpg"),
    ("medium", "dataset/medium_2.jpg"),
    ("medium", "dataset/medium_3.jpg"),
    ("large",  "dataset/large_1.jpg"),
    ("large",  "dataset/large_2.jpg"),
    ("large",  "dataset/large_3.jpg"),
]

CSV_FIELDS = [
    "timestamp",
    "platform",
    "test_type",
    "image_key",
    "image_tier",
    "run_number",
    "total_latency_seconds",
    "processing_seconds",
    "original_size_bytes",
    "original_dimensions",
    "status",
    "error",
]



# Platform invocation helpers
def invoke_aws(url, bucket, key):
    """Send one request to AWS Lambda via API Gateway and return timing data."""
    payload = {"bucket": bucket, "key": key}
    t_start = time.time()
    response = requests.post(url, json=payload, timeout=120)
    total_latency = round(time.time() - t_start, 4)

    response.raise_for_status()
    data = response.json()

    return {
        "total_latency_seconds": total_latency,
        "processing_seconds": data.get("duration_seconds"),
        "original_size_bytes": data.get("original_size_bytes"),
        "original_dimensions": data.get("original_dimensions"),
        "status": "ok",
        "error": "",
    }


def invoke_gcp(url, key):
    """Send one request to GCP Cloud Functions and return timing data."""
    payload = {"key": key}
    t_start = time.time()
    response = requests.post(url, json=payload, timeout=120)
    total_latency = round(time.time() - t_start, 4)

    response.raise_for_status()
    raw_data = response.json()
    data=json.loads(raw_data.get("body", "{}")) 

    return {
        "total_latency_seconds": total_latency,
        "processing_seconds": data.get("duration_seconds"),
        "original_size_bytes": data.get("original_size_bytes"),
        "original_dimensions": data.get("original_dimensions"),
        "status": "ok",
        "error": "",
    }



# Benchmark routines
def run_sequential(platform, invoke_fn, runs, writer):
    """
    Sequential benchmark: call each image `runs` times one after another.
    The very first call per image is tagged as the potential cold start.
    """
    print(f"\n[{platform.upper()}] Sequential benchmark ({runs} runs per image)...")

    for tier, key in IMAGES:
        for run in range(1, runs + 1):
            test_type = "cold_start" if run == 1 else "warm"
            print(f"  [{test_type}] {key} run {run}/{runs} ... ", end="", flush=True)

            try:
                result = invoke_fn(key)
                print(f"{result['total_latency_seconds']}s (processing: {result['processing_seconds']}s)")
            except Exception as e:
                result = {
                    "total_latency_seconds": None,
                    "processing_seconds": None,
                    "original_size_bytes": None,
                    "original_dimensions": None,
                    "status": "error",
                    "error": str(e),
                }
                print(f"ERROR - {e}")

            writer.writerow({
                "timestamp": datetime.utcnow().isoformat(),
                "platform": platform,
                "test_type": test_type,
                "image_key": key,
                "image_tier": tier,
                "run_number": run,
                **result,
            })


def run_concurrency(platform, invoke_fn, concurrency, writer):
    """
    Concurrency benchmark: fire `concurrency` simultaneous requests for a
    representative image from each tier.
    """
    print(f"\n[{platform.upper()}] Concurrency benchmark ({concurrency} simultaneous requests)...")

    # One representative image per tier
    targets = [
        ("small",  "dataset/small_1.jpg"),
        ("medium", "dataset/medium_1.jpg"),
        ("large",  "dataset/large_1.jpg"),
    ]

    for tier, key in targets:
        print(f"  {key} x{concurrency} concurrent ... ", end="", flush=True)

        futures_map = {}
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            for i in range(concurrency):
                future = executor.submit(invoke_fn, key)
                futures_map[future] = i + 1

        latencies = []
        for future, req_num in futures_map.items():
            try:
                result = future.result()
                latencies.append(result["total_latency_seconds"])
                writer.writerow({
                    "timestamp": datetime.utcnow().isoformat(),
                    "platform": platform,
                    "test_type": "concurrency",
                    "image_key": key,
                    "image_tier": tier,
                    "run_number": req_num,
                    **result,
                })
            except Exception as e:
                writer.writerow({
                    "timestamp": datetime.utcnow().isoformat(),
                    "platform": platform,
                    "test_type": "concurrency",
                    "image_key": key,
                    "image_tier": tier,
                    "run_number": req_num,
                    "total_latency_seconds": None,
                    "processing_seconds": None,
                    "original_size_bytes": None,
                    "original_dimensions": None,
                    "status": "error",
                    "error": str(e),
                })

        if latencies:
            print(f"avg={statistics.mean(latencies):.4f}s  min={min(latencies):.4f}s  max={max(latencies):.4f}s")



# Summary printer
def print_summary(output_file):
    """Read the CSV and print a simple summary table per platform/tier/test_type."""
    rows = []
    with open(output_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "ok" and row["total_latency_seconds"]:
                rows.append(row)

    # Group by (platform, image_tier, test_type)
    groups = {}
    for row in rows:
        key = (row["platform"], row["image_tier"], row["test_type"])
        groups.setdefault(key, []).append(float(row["total_latency_seconds"]))

    print("\n" + "=" * 70)
    print(f"{'Platform':<10} {'Tier':<8} {'Test Type':<15} {'Avg (s)':<10} {'Min (s)':<10} {'Max (s)':<10} {'N'}")
    print("-" * 70)
    for (platform, tier, test_type), latencies in sorted(groups.items()):
        print(
            f"{platform:<10} {tier:<8} {test_type:<15} "
            f"{statistics.mean(latencies):<10.4f} {min(latencies):<10.4f} {max(latencies):<10.4f} {len(latencies)}"
        )
    print("=" * 70)
    print(f"\nFull results saved to: {output_file}")



# Entry point
def main():
    parser = argparse.ArgumentParser(description="Benchmark AWS Lambda and GCP Cloud Functions")
    parser.add_argument("--aws-url",    required=False, help="AWS API Gateway endpoint URL")
    parser.add_argument("--aws-bucket", required=False, help="S3 bucket name containing the dataset")
    parser.add_argument("--gcp-url",    required=False, help="GCP Cloud Functions endpoint URL")
    parser.add_argument("--runs",       type=int, default=5,  help="Number of sequential runs per image (default: 5)")
    parser.add_argument("--concurrency",type=int, default=10, help="Number of simultaneous requests for concurrency test (default: 10)")
    parser.add_argument("--output",     default="results.csv", help="Output CSV file (default: results.csv)")
    args = parser.parse_args()

    if not args.aws_url and not args.gcp_url:
        parser.error("Provide at least one of --aws-url or --gcp-url")

    if args.aws_url and not args.aws_bucket:
        parser.error("--aws-bucket is required when --aws-url is provided")

    print(f"Benchmark started at {datetime.utcnow().isoformat()} UTC")
    print(f"Runs per image: {args.runs}  |  Concurrency: {args.concurrency}  |  Output: {args.output}")

    with open(args.output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()

        # AWS benchmark
        if args.aws_url:
            aws_invoke = lambda key: invoke_aws(args.aws_url, args.aws_bucket, key)
            run_sequential("aws", aws_invoke, args.runs, writer)
            run_concurrency("aws", aws_invoke, args.concurrency, writer)

        # GCP benchmark
        if args.gcp_url:
            gcp_invoke = lambda key: invoke_gcp(args.gcp_url, key)
            run_sequential("gcp", gcp_invoke, args.runs, writer)
            run_concurrency("gcp", gcp_invoke, args.concurrency, writer)

    print_summary(args.output)


if __name__ == "__main__":
    main()
