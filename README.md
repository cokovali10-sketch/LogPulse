# LogPulse

Advanced log analyzer with multi-format parsing, filtering, and comprehensive reporting.

**Version:** 1.0.0 | **Language:** Python | **License:** MIT

## Features

### Core Capabilities
- **Multi-format parsing** — syslog, Apache, Nginx, Windows Event Log, JSON-line, generic timestamp+level formats
- **Smart detection** — auto-detects log format per line, mixed formats supported
- **Streaming analysis** — process files line-by-line for memory efficiency
- **Batch & directory scanning** — analyze single files, multiple files, or entire directories

### Filtering Engine
- **Level filtering** — min/max severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Source filtering** — filter by program, IP, or application name
- **Time range filtering** — specify start/end datetime bounds
- **Keyword search** — find entries containing specific terms
- **Regex patterns** — full regex support across message, source, or any field
- **Exclude rules** — remove specific levels or sources from results
- **Custom predicates** — pass any function for advanced filtering

### Report Formats
- **Text** — human-readable terminal output with bar charts and statistics
- **JSON** — structured data for programmatic consumption
- **CSV** — spreadsheet-compatible export
- **HTML** — styled report with color-coded levels and error summaries

### Analytics
- **Level distribution** — count and percentage per severity
- **Source breakdown** — which applications generate the most logs
- **Hourly distribution** — identify peak activity times
- **Error tracking** — errors grouped by source with line numbers
- **Top messages** — most frequent log messages (deduplicated)
- **Time range** — first and last timestamp detection

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python -m logpulse.cli [options] <paths...>
```

## CLI Usage

```bash
# Analyze a single log file
logpulse /var/log/app.log

# Analyze entire directory
logpulse /var/log/ --format json -o report.json

# Filter by level (ERROR and above only)
logpulse app.log -l ERROR

# Filter by source
logpulse app.log -s server.api -s server.db

# Keyword search
logpulse app.log -k timeout -k connection refused

# Regex pattern matching
logpulse app.log -r "5\d{2}"  # HTTP 5xx errors

# Time range filtering
logpulse app.log --start "2024-01-01 00:00:00" --end "2024-01-31 23:59:59"

# Generate HTML report
logpulse app.log logs/ -f html -o report.html

# Show only statistics
logpulse app.log --stats
```

## Programmatic API

```python
from logpulse.analyzer import LogAnalyzer
from logpulse.filter import LogFilter

# Create analyzer and load data
analyzer = LogAnalyzer()
analyzer.load_file("app.log")
analyzer.load_directory("/var/log")
analyzer.load_string("2024-01-15 10:30:01 INFO server.app Started")

# Apply filters
log_filter = analyzer.filter()
log_filter.by_level(min_level="ERROR")
log_filter.by_source("server.api")
log_filter.by_keyword("timeout")
filtered = analyzer.apply_filter(log_filter)

# Generate reports
report = filtered.report()
print(report.to_text())      # Human-readable
print(report.to_json())      # JSON
print(report.to_csv())       # CSV
print(report.to_html())      # HTML report

# Quick stats
print(analyzer.stats)
# {'total_entries': 156, 'levels': {'ERROR': 23, 'INFO': 120}, ...}
```

## Supported Log Formats

| Format | Example | Parser |
|--------|---------|--------|
| Generic | `2024-01-15 10:30:01 INFO app.message` | `COMMON_PATTERN` |
| Syslog | `Jan 15 10:30:01 host prog[pid]: msg` | `SYSLOG_PATTERN` |
| Apache | `192.168.1.1 - user [date] "GET / HTTP/1.1" 200 1234` | `APACHE_PATTERN` |
| Nginx | Same as Apache + request_time field | `NGINX_PATTERN` |
| Windows Event | `2024-01-15 10:30:01 Error Source - message` | `WINDOWS_EVENT_PATTERN` |
| JSON-line | `{"timestamp":"...","level":"INFO","message":"..."}` | JSON parser |

## Tests

```bash
cd LogPulse
python tests/test_all.py
```

Runs 23 tests covering parsing, filtering, reporting, and edge cases.

## Project Structure

```
LogPulse/
├── logpulse/
│   ├── __init__.py      # Package metadata
│   ├── parser.py        # Log line parsing (6 formats)
│   ├── filter.py        # Filtering engine
│   ├── report.py        # Report generation (4 formats)
│   ├── analyzer.py      # Main analyzer orchestrator
│   └── cli.py           # CLI interface
├── tests/
│   └── test_all.py      # 23 unit tests
├── setup.py             # Package configuration
└── README.md
```

## License

MIT
