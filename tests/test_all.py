"""Tests for LogPulse."""

import os
import sys
import json
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logpulse.parser import parse_log_line, LEVELS
from logpulse.filter import LogFilter
from logpulse.analyzer import LogAnalyzer
from logpulse.report import ReportGenerator, LiveDashboard, tail_log


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

NGINX_SAMPLE = """192.168.1.1 - - [15/Jan/2024:10:30:01 +0000] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0" 0.015
192.168.1.2 - admin [15/Jan/2024:10:30:02 +0000] "POST /login HTTP/1.1" 500 567 "-" "curl/7.68" 0.320
"""

WINDOWS_SAMPLE = """2024-01-15 10:30:01 Information Service Control Manager - The following service was installed: MyService
2024-01-15 10:30:02 Warning Disk - Disk 0 has been replaced with a different disk
2024-01-15 10:30:03 Error Application Popup - Application popup: System Error
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


def test_parse_nginx():
    entry = parse_log_line(NGINX_SAMPLE.strip().splitlines()[0], 1)
    assert entry is not None
    assert entry.extra["status"] == 200
    assert entry.extra["method"] == "GET"
    assert entry.extra["size"] == "1234"


def test_parse_nginx_error():
    entry = parse_log_line(NGINX_SAMPLE.strip().splitlines()[1], 1)
    assert entry is not None
    assert entry.level == "ERROR"
    assert entry.extra["status"] == 500


def test_parse_windows_event():
    entry = parse_log_line(WINDOWS_SAMPLE.strip().splitlines()[0], 1)
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.source == "Service Control Manager"


def test_parse_windows_event_warning():
    entry = parse_log_line(WINDOWS_SAMPLE.strip().splitlines()[1], 1)
    assert entry is not None
    assert entry.level == "WARNING"


def test_parse_windows_event_error():
    entry = parse_log_line(WINDOWS_SAMPLE.strip().splitlines()[2], 1)
    assert entry is not None
    assert entry.level == "ERROR"


def test_filter_regex():
    entries = []
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        e = parse_log_line(line, i)
        if e:
            entries.append(e)
    f = LogFilter().by_regex(r"timeout|refused")
    result = f.apply(entries)
    assert len(result) >= 2


def test_filter_time_range():
    entries = []
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        e = parse_log_line(line, i)
        if e:
            entries.append(e)
    from datetime import datetime
    f = LogFilter().by_time_range(
        start=datetime(2024, 1, 15, 10, 30, 0),
        end=datetime(2024, 1, 15, 11, 0, 0),
    )
    result = f.apply(entries)
    assert len(result) == 6


def test_exclude_level():
    entries = []
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        e = parse_log_line(line, i)
        if e:
            entries.append(e)
    f = LogFilter().exclude_level("INFO")
    result = f.apply(entries)
    assert all(e.level != "INFO" for e in result)


def test_report_html_with_errors():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    html = analyzer.report().to_html()
    assert "Errors" in html or "ERROR" in html


def test_analyzer_multiple_loads():
    analyzer = LogAnalyzer()
    analyzer.load_string(SAMPLE_LOGS)
    analyzer.load_string(SYSLOG_SAMPLE)
    assert len(analyzer.entries) == 10


def test_level_num():
    entry = parse_log_line(SAMPLE_LOGS.strip().splitlines()[0], 1)
    assert entry.level_num == 1  # INFO
    entry = parse_log_line(SAMPLE_LOGS.strip().splitlines()[3], 1)
    assert entry.level_num == 3  # ERROR


def test_live_dashboard_counts():
    dashboard = LiveDashboard(use_color=False)
    entry = parse_log_line(SAMPLE_LOGS.strip().splitlines()[0], 1)
    dashboard.on_entry(entry)
    assert dashboard._count == 1
    assert dashboard._level_counts["INFO"] == 1


def test_live_dashboard_summary():
    dashboard = LiveDashboard(use_color=False)
    for i, line in enumerate(SAMPLE_LOGS.strip().splitlines(), 1):
        entry = parse_log_line(line, i)
        if entry:
            dashboard.on_entry(entry)
    assert dashboard._count == 8
    assert dashboard._level_counts["ERROR"] == 2
    assert dashboard._level_counts["CRITICAL"] == 1


def test_tail_log_basic():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write(SAMPLE_LOGS)
        f.flush()
        path = f.name
    try:
        entries = list(tail_log(path, follow=False))
        assert len(entries) == 8
        assert entries[0].level == "INFO"
    finally:
        os.unlink(path)


def test_tail_log_new_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write(SAMPLE_LOGS)
        f.flush()
        path = f.name

    collected = []

    def writer():
        time.sleep(0.3)
        with open(path, "a", encoding="utf-8") as af:
            af.write("2024-01-15 13:00:00 ERROR server.new New error appended\n")
        time.sleep(0.5)

    try:
        t = threading.Thread(target=writer)
        t.start()
        for entry in tail_log(path, follow=True, poll_interval=0.1):
            collected.append(entry)
            if len(collected) >= 9:
                break
        t.join(timeout=3)
        assert len(collected) >= 9
        assert collected[-1].source == "server.new"
    finally:
        os.unlink(path)


PAPER_SAMPLE = """[12:43:22] [ServerMain/INFO]: Loading properties
[12:43:22] [Server thread/ERROR]: [ModernPluginLoadingStrategy] Ambiguous plugin name 'X'
[12:43:24] [Server thread/WARN]: Plugin Y tried to register permission
[14:00:01] [Craft Scheduler Thread - 3 - AuctionHouse/WARN]: slow task
[12:43:10 INFO]: short form line
"""


def test_paper_format():
    entries = [e for e in (parse_log_line(line, i) for i, line in enumerate(PAPER_SAMPLE.strip().splitlines(), 1)) if e]
    assert len(entries) == 5
    assert entries[0].level == "INFO"
    assert entries[0].source == "ServerMain"
    assert entries[1].level == "ERROR"
    assert entries[2].level == "WARNING"
    assert entries[3].source == "Craft Scheduler Thread - 3 - AuctionHouse"
    assert entries[3].level == "WARNING"
    assert entries[4].level == "INFO"
    assert entries[4].source == "unknown"
    assert entries[0].timestamp is not None
    assert entries[0].timestamp.hour == 12 and entries[0].timestamp.minute == 43


def test_report_version():
    from logpulse import __version__
    assert __version__ == "1.1.0"


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
