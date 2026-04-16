#!/usr/bin/env python3
"""
benchmark.py - Benchmark AWS Lambda and GCP Cloud Functions for image processing.

Modes:
  cold        Send 1 request per image after 30+ minutes of idle time.
  warm        Send 100 sequential requests per image and record average latency.
  concurrency Fire 50, 100, and 500 simultaneous requests using asyncio.
  all         Run cold → warm → concurrency in sequence.

Usage:
    python benchmark.py --mode cold        --aws-url <URL> --aws-bucket <BUCKET> [--gcp-url <URL>]
    python benchmark.py --mode warm        --aws-url <URL> --aws-bucket <BUCKET> [--gcp-url <URL>]
    python benchmark.py --mode concurrency --aws-url <URL> --aws-bucket <BUCKET> [--gcp-url <URL>]
    python benchmark.py --mode all         --aws-url <URL> --aws-bucket <BUCKET> [--gcp-url <URL>]

Example:
    python benchmark.py --mode all \\
        --aws-url https://abc123.execute-api.us-east-1.amazonaws.com/Prod/process \\
        --aws-bucket cs4296-image-benchmark-123456789012 \\
        --gcp-url https://us-central1-project.cloudfunctions.net/process_image \\
        --output results.csv
"""

import argparse
import asyncio
import csv
import json
import statistics
import time
from datetime import datetime

import aiohttp
import requests

# ---------------------------------------------------------------------------
# Images grouped by tier
# ---------------------------------------------------------------------------
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

# One representative image per tier used for warm + concurrency tests
TIER_REPRESENTATIVES = [
    ("small",  "dataset/small_1.jpg"),
    ("medium", "dataset/medium_1.jpg"),
    ("large",  "dataset/large_1.jpg"),
]

CONCURRENCY_LEVELS = [50, 100, 500]

WARM_RUNS = 100

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


# ---------------------------------------------------------------------------
# Synchronous invoke helpers (used for cold + warm tests)
# ---------------------------------------------------------------------------

def invoke_aws(url, bucket, key):
    """POST one request to AWS Lambda via API Gateway and return timing data."""
    payload = {"bucket": bucket, "key": key}
    t_start = time.perf_counter()
    response = requests.post(url, json=payload, timeout=120)
    total_latency = round(time.perf_counter() - t_start, 4)

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
    """POST one request to GCP Cloud Functions and return timing data."""
    payload = {"key": key}
    t_start = time.perf_counter()
    response = requests.post(url, json=payload, timeout=120)
    total_latency = round(time.perf_counter() - t_start, 4)

    response.raise_for_status()
    raw_data = response.json()
    data = json.loads(raw_data.get("body", "{}"))

    return {
        "total_latency_seconds": total_latency,
        "processing_seconds": data.get("duration_seconds"),
        "original_size_bytes": data.get("original_size_bytes"),
        "original_dimensions": data.get("original_dimensions"),
        "status": "ok",
        "error": "",
    }


# ---------------------------------------------------------------------------
# Async invoke helpers (used for concurrency test)
# ---------------------------------------------------------------------------

async def async_invoke_aws(session, url, bucket, key):
    payload = {"bucket": bucket, "key": key}
    t_start = time.perf_counter()
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            total_latency = round(time.perf_counter() - t_start, 4)
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            return {
                "total_latency_seconds": total_latency,
                "processing_seconds": data.get("duration_seconds"),
                "original_size_bytes": data.get("original_size_bytes"),
                "original_dimensions": data.get("original_dimensions"),
                "status": "ok",
                "error": "",
            }
    except Exception as e:
        return {
            "total_latency_seconds": round(time.perf_counter() - t_start, 4),
            "processing_seconds": None,
            "original_size_bytes": None,
            "original_dimensions": None,
            "status": "error",
            "error": str(e),
        }


async def async_invoke_gcp(session, url, key):
    payload = {"key": key}
    t_start = time.perf_counter()
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            total_latency = round(time.perf_counter() - t_start, 4)
            resp.raise_for_status()
            raw_data = await resp.json(content_type=None)
            data = json.loads(raw_data.get("body", "{}"))
            return {
                "total_latency_seconds": total_latency,
                "processing_seconds": data.get("duration_seconds"),
                "original_size_bytes": data.get("original_size_bytes"),
                "original_dimensions": data.get("original_dimensions"),
                "status": "ok",
                "error": "",
            }
    except Exception as e:
        return {
            "total_latency_seconds": round(time.perf_counter() - t_start, 4),
            "processing_seconds": None,
            "original_size_bytes": None,
            "original_dimensions": None,
            "status": "error",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Tail-latency helper
# ---------------------------------------------------------------------------

def percentile(sorted_data, pct):
    """Return the pct-th percentile from a pre-sorted list."""
    if not sorted_data:
        return None
    k = (len(sorted_data) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return round(sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo), 4)


# ---------------------------------------------------------------------------
# Test routines
# ---------------------------------------------------------------------------

def run_cold_start(platform, invoke_fn, writer):
    """
    Send exactly ONE request per image after the function has been idle.
    The caller is responsible for ensuring 30+ minutes of idle time first.
    """
    print(f"\n[{platform.upper()}] Cold-start test (1 request per image)...")

    for tier, key in IMAGES:
        print(f"  [cold_start] {key} ... ", end="", flush=True)
        try:
            result = invoke_fn(key)
            print(f"{result['total_latency_seconds']}s")
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
            "test_type": "cold_start",
            "image_key": key,
            "image_tier": tier,
            "run_number": 1,
            **result,
        })


def run_warm(platform, invoke_fn, writer):
    """
    Send WARM_RUNS sequential requests per representative image and record
    per-request latency plus a final average summary.
    """
    print(f"\n[{platform.upper()}] Warm-start test ({WARM_RUNS} sequential requests per image)...")

    for tier, key in TIER_REPRESENTATIVES:
        latencies = []
        print(f"  {key} x{WARM_RUNS} sequential:")
        for run in range(1, WARM_RUNS + 1):
            print(f"    run {run}/{WARM_RUNS} ... ", end="", flush=True)
            try:
                result = invoke_fn(key)
                latencies.append(result["total_latency_seconds"])
                print(f"{result['total_latency_seconds']}s")
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
                "test_type": "warm",
                "image_key": key,
                "image_tier": tier,
                "run_number": run,
                **result,
            })

        if latencies:
            print(
                f"  -> avg={statistics.mean(latencies):.4f}s  "
                f"min={min(latencies):.4f}s  max={max(latencies):.4f}s"
            )


async def _fire_concurrent(async_invoke_fn, concurrency):
    """Launch `concurrency` async requests simultaneously and return all results."""
    connector = aiohttp.TCPConnector(limit=0)  # no cap on simultaneous connections
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [async_invoke_fn(session) for _ in range(concurrency)]
        return await asyncio.gather(*tasks, return_exceptions=False)


def run_concurrency(platform, async_invoke_fn, writer):
    """
    Fire CONCURRENCY_LEVELS simultaneous requests using asyncio for each
    representative image. Records per-request rows and prints tail latency.
    """
    print(f"\n[{platform.upper()}] Concurrency test (levels: {CONCURRENCY_LEVELS})...")

    for tier, key in TIER_REPRESENTATIVES:
        for concurrency in CONCURRENCY_LEVELS:
            print(f"  {key} x{concurrency} concurrent ... ", end="", flush=True)

            bound_fn = lambda session, _key=key: async_invoke_fn(session, _key)
            results = asyncio.run(_fire_concurrent(bound_fn, concurrency))

            latencies = []
            failures = 0
            for req_num, result in enumerate(results, start=1):
                if result["status"] == "error":
                    failures += 1
                else:
                    latencies.append(result["total_latency_seconds"])

                writer.writerow({
                    "timestamp": datetime.utcnow().isoformat(),
                    "platform": platform,
                    "test_type": f"concurrency_{concurrency}",
                    "image_key": key,
                    "image_tier": tier,
                    "run_number": req_num,
                    **result,
                })

            failure_rate = round(failures / concurrency * 100, 1)
            if latencies:
                sl = sorted(latencies)
                print(
                    f"avg={statistics.mean(sl):.4f}s  "
                    f"p50={percentile(sl, 50):.4f}s  "
                    f"p95={percentile(sl, 95):.4f}s  "
                    f"p99={percentile(sl, 99):.4f}s  "
                    f"failures={failures}/{concurrency} ({failure_rate}%)"
                )
            else:
                print(f"ALL FAILED ({concurrency}/{concurrency})")


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(output_file):
    """Read the CSV and print a summary table per platform / tier / test_type."""
    rows = []
    with open(output_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "ok" and row["total_latency_seconds"]:
                rows.append(row)

    # Group by (platform, image_tier, test_type)
    groups = {}
    for row in rows:
        group_key = (row["platform"], row["image_tier"], row["test_type"])
        groups.setdefault(group_key, []).append(float(row["total_latency_seconds"]))

    print("\n" + "=" * 95)
    print(
        f"{'Platform':<10} {'Tier':<8} {'Test Type':<22} "
        f"{'Avg(s)':<9} {'Min(s)':<9} {'p50(s)':<9} {'p95(s)':<9} {'p99(s)':<9} {'N'}"
    )
    print("-" * 95)
    for (platform, tier, test_type), latencies in sorted(groups.items()):
        sl = sorted(latencies)
        print(
            f"{platform:<10} {tier:<8} {test_type:<22} "
            f"{statistics.mean(sl):<9.4f} {min(sl):<9.4f} "
            f"{percentile(sl, 50):<9.4f} {percentile(sl, 95):<9.4f} {percentile(sl, 99):<9.4f} "
            f"{len(sl)}"
        )
    print("=" * 95)
    print(f"\nFull results saved to: {output_file}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark AWS Lambda and GCP Cloud Functions — cold, warm, concurrency"
    )
    parser.add_argument(
        "--mode",
        choices=["cold", "warm", "concurrency", "all"],
        default="all",
        help="Which test(s) to run (default: all)",
    )
    parser.add_argument("--aws-url",    required=False, help="AWS API Gateway endpoint URL")
    parser.add_argument("--aws-bucket", required=False, help="S3 bucket name containing the dataset")
    parser.add_argument("--gcp-url",    required=False, help="GCP Cloud Functions endpoint URL")
    parser.add_argument(
        "--output", default="results.csv", help="Output CSV file (default: results.csv)"
    )
    args = parser.parse_args()

    if not args.aws_url and not args.gcp_url:
        parser.error("Provide at least one of --aws-url or --gcp-url")
    if args.aws_url and not args.aws_bucket:
        parser.error("--aws-bucket is required when --aws-url is provided")

    # Cold-start reminder
    if args.mode in ("cold", "all"):
        print("\n*** COLD-START REMINDER ***")
        print("Make sure your functions have been completely idle for 30+ minutes.")
        print("Check AWS CloudWatch / GCP Logs to confirm no recent invocations.")
        confirm = input("Have the functions been idle for 30+ minutes? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborting. Wait for 30+ minutes of idle time, then re-run.")
            return

    print(f"\nBenchmark started at {datetime.utcnow().isoformat()} UTC")
    print(f"Mode: {args.mode}  |  Output: {args.output}")

    with open(args.output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()

        # ---- AWS ----
        if args.aws_url:
            aws_sync = lambda key: invoke_aws(args.aws_url, args.aws_bucket, key)
            aws_async = lambda session, key: async_invoke_aws(
                session, args.aws_url, args.aws_bucket, key
            )

            if args.mode in ("cold", "all"):
                run_cold_start("aws", aws_sync, writer)

            if args.mode in ("warm", "all"):
                run_warm("aws", aws_sync, writer)

            if args.mode in ("concurrency", "all"):
                run_concurrency("aws", aws_async, writer)

        # ---- GCP ----
        if args.gcp_url:
            gcp_sync = lambda key: invoke_gcp(args.gcp_url, key)
            gcp_async = lambda session, key: async_invoke_gcp(session, args.gcp_url, key)

            if args.mode in ("cold", "all"):
                run_cold_start("gcp", gcp_sync, writer)

            if args.mode in ("warm", "all"):
                run_warm("gcp", gcp_sync, writer)

            if args.mode in ("concurrency", "all"):
                run_concurrency("gcp", gcp_async, writer)

    print_summary(args.output)


if __name__ == "__main__":
    main()
