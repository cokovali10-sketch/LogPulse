# LogPulse

Advanced log analyzer with filtering and multi-format reporting.

## Features

- Parse common log formats: syslog, Apache, JSON-line, generic timestamp+level
- Filter by level, source, time range, keyword, regex
- Reports: text, JSON, CSV, HTML
- Hourly distribution, error tracking, source statistics
- Works on files and directories

## Usage

```bash
# Analyze a single file
python -m logpulse.cli access.log

# Filter errors only
python -m logpulse.cli app.log -l ERROR

# JSON report to file
python -m logpulse.cli logs/ -f json -o report.json

# HTML report
python -m logpulse.cli app.log -f html -o report.html

# Keyword search
python -m logpulse.cli app.log -k timeout -k connection

# Time range
python -m logpulse.cli app.log --start "2024-01-01 00:00:00" --end "2024-01-31 23:59:59"
```

## Programmatic Use

```python
from logpulse.analyzer import LogAnalyzer

analyzer = LogAnalyzer()
analyzer.load_file("app.log")
analyzer.load_directory("/var/log")

# Filter
log_filter = analyzer.filter().by_level(min_level="ERROR")
filtered = analyzer.apply_filter(log_filter)

# Report
report = filtered.report()
print(report.to_text())
print(report.to_json())
```

## Installation

```bash
pip install -e .
```

## License

MIT
