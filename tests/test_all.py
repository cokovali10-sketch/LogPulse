"""Tests for LogPulse."""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logpulse.parser import parse_log_line, LEVELS
from logpulse.filter import LogFilter
from logpulse.analyzer import LogAnalyzer
from logpulse.report import ReportGenerator


SAMPLE_LOGS = """2024-01-15 10:30:01 INFO server.app Starting application
2024-01-15 10:30:02 DEBUG server.db Connected to database
2024-01-15 10:30:05 WARNING server.cache Cache miss for key user_42
2024-01-15 10:30:10 ERROR server.api Request timeout after 30s
2024-01-15 10:30:15 CRITICAL server.core Unhandled exception in worker
2024-01-15 11:00:00 INFO server.auth User login: admin
2024-01-15 11:00:05 ERROR server.api Connection refused to upstream
2024-01-15 12:00:00 INFO server.app Shutdown initiated
"""

SYSLOG_SAMPLE = """Jan 15 10:30:01 myhost sshd[1234]: Accepted publickey for user from 192.168.1.1
Jan 15 10:30:02 myhost kernel: [12345.678] Out of memory: Killed process 5678
"""

APACHE_SAMPLE = """192.168.1.1 - admin [15/Jan/2024:10:30:01 +0000] "GET /api/users HTTP/1.1" 200 1234
192.168.1.2 - - [15/Jan/2024:10:30:02 +0000] "POST /login HTTP/1.1" 401 567
"""

JSON_SAMPLE = """{"timestamp":"2024-01-15T10:30:01Z","level":"INFO","source":"app.main","message":"Server started"}
{"timestamp":"2024-01-15T10:30:02Z","level":"ERROR","source":"app.db","message":"Connection timeout"}
"""


def test_parse_common():
    entry = parse_log_line(SAMPLE_LOGS.strip().splitlines()[0], 1)
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.source == "server.app"
    assert "Starting" in entry.message
    assert entry.timestamp is not None


def test_parse_syslog():
    entry = parse_log_line(SYSLOG_SAMPLE.strip().splitlines()[0], 1)
    assert entry is not None
    assert entry.source == "sshd"
    assert "Accepted" in entry.message


def test_parse_apache():
    entry = parse_log_line(APACHE_SAMPLE.strip().splitlines()[0], 1)
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.extra["status"] == 200


def test_parse_json_line():
    entry = parse_log_line(JSON_SAMPLE.strip().splitlines()[0], 1)
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.source == "app.main"


def test_filter_level():
    entries = []
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        e = parse_log_line(line, i)
        if e:
            entries.append(e)
    f = LogFilter().by_level(min_level="ERROR")
    result = f.apply(entries)
    assert all(e.level in ("ERROR", "CRITICAL") for e in result)
    assert len(result) == 3


def test_filter_source():
    entries = []
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        e = parse_log_line(line, i)
        if e:
            entries.append(e)
    f = LogFilter().by_source("server.api")
    result = f.apply(entries)
    assert all(e.source == "server.api" for e in result)


def test_filter_keyword():
    entries = []
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        e = parse_log_line(line, i)
        if e:
            entries.append(e)
    f = LogFilter().by_keyword("timeout")
    result = f.apply(entries)
    assert len(result) >= 1


def test_analyzer_load_string():
    analyzer = LogAnalyzer()
    count = analyzer.load_string(SAMPLE_LOGS)
    assert count == 8
    assert len(analyzer.entries) == 8


def test_report_text():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    report = analyzer.report().to_text()
    assert "LogPulse Report" in report
    assert "ERROR" in report


def test_report_json():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    output = analyzer.report().to_json()
    data = json.loads(output)
    assert "level_counts" in data
    assert "source_counts" in data


def test_report_csv():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    csv_out = analyzer.report().to_csv()
    assert "line,timestamp,level,source,message" in csv_out


def test_report_html():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    html = analyzer.report().to_html()
    assert "<!DOCTYPE html>" in html
    assert "LogPulse Report" in html


def test_full_pipeline():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    f = analyzer.filter().by_level(min_level="WARNING")
    filtered = analyzer.apply_filter(f)
    report = filtered.report()
    assert report.generate().filtered_lines == 4
    text = report.to_text()
    assert "WARNING" in text


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
