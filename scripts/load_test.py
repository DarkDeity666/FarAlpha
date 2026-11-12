#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import random
import string
import time
import urllib.request


def random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def send_get_root(base_url):
    try:
        start = time.time()
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200, time.time() - start
    except Exception:
        return False, 0


def send_post_data(base_url):
    try:
        start = time.time()
        payload = json.dumps({"key": random_string(), "val": random_string(16)}).encode()
        req = urllib.request.Request(
            f"{base_url}/data",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 201, time.time() - start
    except Exception:
        return False, 0


def send_get_data(base_url):
    try:
        start = time.time()
        req = urllib.request.Request(f"{base_url}/data")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200, time.time() - start
    except Exception:
        return False, 0


def worker(base_url, duration, results):
    end_time = time.time() + duration
    while time.time() < end_time:
        r = random.random()
        if r < 0.4:
            ok, lat = send_post_data(base_url)
        elif r < 0.8:
            ok, lat = send_get_data(base_url)
        else:
            ok, lat = send_get_root(base_url)
        results.append((ok, lat))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    print(f"Testing {args.url} with {args.concurrency} threads for {args.duration}s...")
    results = []
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(worker, args.url, args.duration, results) for _ in range(args.concurrency)]
        concurrent.futures.wait(futures)

    elapsed = time.time() - start
    total = len(results)
    ok = sum(1 for r in results if r[0])
    lats = [r[1] for r in results if r[0]]

    print("\nResults:")
    print(f"Total: {total}")
    print(f"Success: {ok} ({ok/total*100:.1f}%)" if total else "No requests")
    print(f"RPS: {total/elapsed:.1f}")
    if lats:
        print(f"Avg latency: {sum(lats)/len(lats)*1000:.1f}ms")


if __name__ == "__main__":
    main()
