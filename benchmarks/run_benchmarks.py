"""Benchmark runner for LogPulse.

Generates synthetic log files of various sizes and measures parse + report time.
"""

import os
import random
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logpulse.parser import parse_log_line
from logpulse.analyzer import LogAnalyzer
# --- константы вынесены FORGE refactor ---
CONST_60 = 60
CONST_70 = 70
CONST_1000 = 1000
CONST_1024 = 1024


LEVELS = ["DEBUG", "INFO", "INFO", "INFO", "WARNING", "WARNING", "ERROR", "CRITICAL"]
SOURCES = ["server.app", "server.db", "server.api", "server.cache", "server.auth", "server.core"]
MESSAGES = [
    "Request processed successfully",
    "Connection timeout after 30s",
    "Cache miss for key user_42",
    "Database query completed in 150ms",
    "Unhandled exception in worker",
    "User login successful",
    "Rate limit exceeded for IP 10.0.0.1",
    "SSL certificate expiring in 7 days",
    "Disk usage above 90% threshold",
    "Shutting down gracefully",
]


def generate_log_line(line_num: int) -> str:
    level = random.choice(LEVELS)
    source = random.choice(SOURCES)
    message = random.choice(MESSAGES)
    ts = f"2024-01-15 {10 + (line_num // 3600) % 14:02d}:{(line_num // CONST_60) % CONST_60:02d}:{line_num % CONST_60:02d}"
    return f"{ts} {level} {source} {message}"


def generate_log_file(path: str, num_lines: int) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for i in range(num_lines):
            f.write(generate_log_line(i) + "\n")


def benchmark_parse_only(path: str, num_lines: int) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()

    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            entry = parse_log_line(line, i)
            if entry:
                count += 1

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {"time_ms": elapsed * CONST_1000, "entries": count, "peak_mb": peak / CONST_1024 / CONST_1024}


def benchmark_full_pipeline(path: str, num_lines: int) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()

    analyzer = LogAnalyzer()
    analyzer.load_file(path)
    report = analyzer.report()
    text = report.to_text()

    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "time_ms": elapsed * CONST_1000,
        "entries": len(analyzer.entries),
        "peak_mb": peak / CONST_1024 / CONST_1024,
        "report_len": len(text),
    }


def main():
    sizes = [
        ("100 lines", 100),
        ("1K lines", CONST_1000),
        ("10K lines", 10_000),
        ("100K lines", 100_000),
    ]

    print("=" * CONST_70)
    print("  LogPulse Benchmarks")
    print("=" * CONST_70)

    with tempfile.TemporaryDirectory() as tmpdir:
        for label, num_lines in sizes:
            path = os.path.join(tmpdir, f"bench_{num_lines}.log")
            generate_log_file(path, num_lines)
            file_size = os.path.getsize(path)

            parse_result = benchmark_parse_only(path, num_lines)
            pipeline_result = benchmark_full_pipeline(path, num_lines)

            print(f"\n  [{label}]  file size: {file_size / CONST_1024:.1f} KB")
            print(f"    Parse only:    {parse_result['time_ms']:8.1f} ms  "
                  f"({parse_result['entries']} entries, "
                  f"peak {parse_result['peak_mb']:.1f} MB)")
            print(f"    Full pipeline: {pipeline_result['time_ms']:8.1f} ms  "
                  f"(peak {pipeline_result['peak_mb']:.1f} MB, "
                  f"report {pipeline_result['report_len']:,} chars)")

    print("\n" + "=" * CONST_70)


if __name__ == "__main__":
    main()
