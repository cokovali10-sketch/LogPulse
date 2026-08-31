"""CLI interface for LogPulse."""

import argparse
import sys
import os
from datetime import datetime

from .analyzer import LogAnalyzer
from .filter import LogFilter


def main():
    parser = argparse.ArgumentParser(
        prog="logpulse",
        description="LogPulse — Advanced Log Analyzer",
    )
    parser.add_argument("paths", nargs="+", help="Log file(s) or directory")
    parser.add_argument("-l", "--level", default=None, help="Min level (DEBUG/INFO/WARNING/ERROR/CRITICAL)")
    parser.add_argument("-L", "--max-level", default=None, help="Max level")
    parser.add_argument("-s", "--source", action="append", default=[], help="Filter by source (repeatable)")
    parser.add_argument("-k", "--keyword", action="append", default=[], help="Filter by keyword (repeatable)")
    parser.add_argument("-r", "--regex", default=None, help="Regex pattern to match")
    parser.add_argument("--start", default=None, help="Start time (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end", default=None, help="End time (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("-f", "--format", choices=["text", "json", "csv", "html"], default="text", help="Output format")
    parser.add_argument("-o", "--output", default=None, help="Output file (default: stdout)")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")

    args = parser.parse_args()

    analyzer = LogAnalyzer()
    for path in args.paths:
        if os.path.isdir(path):
            n = analyzer.load_directory(path)
            print(f"Loaded {n} entries from directory: {path}", file=sys.stderr)
        elif os.path.isfile(path):
            n = analyzer.load_file(path)
            print(f"Loaded {n} entries from file: {path}", file=sys.stderr)
        else:
            print(f"Warning: {path} not found, skipping", file=sys.stderr)

    if not analyzer.entries:
        print("No log entries found.", file=sys.stderr)
        sys.exit(1)

    log_filter = analyzer.filter()
    if args.level:
        log_filter.by_level(min_level=args.level)
    if args.max_level:
        log_filter.by_level(max_level=args.max_level)
    if args.source:
        log_filter.by_source(*args.source)
    if args.keyword:
        log_filter.by_keyword(*args.keyword)
    if args.regex:
        log_filter.by_regex(args.regex)
    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
        log_filter.by_time_range(start=start)
    if args.end:
        end = datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
        log_filter.by_time_range(end=end)

    filtered = analyzer.apply_filter(log_filter)
    report_gen = filtered.report()

    if args.stats:
        output = str(analyzer.stats)
    elif args.format == "json":
        output = report_gen.to_json()
    elif args.format == "csv":
        output = report_gen.to_csv()
    elif args.format == "html":
        output = report_gen.to_html()
    else:
        output = report_gen.to_text()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
