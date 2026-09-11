# LogPulse

Advanced log analyzer with multi-format parsing, filtering, real-time tail monitoring, and comprehensive reporting.

**Version:** 1.1.0 | **Python:** 3.10+ | **License:** MIT | **CI:** GitHub Actions

## Features

### Core Capabilities
- **Multi-format parsing** — syslog, Apache, Nginx, Windows Event Log, JSON-line, generic timestamp+level formats
- **Smart detection** — auto-detects log format per line, mixed formats supported
- **Streaming analysis** — process files line-by-line for memory efficiency
- **Batch & directory scanning** — analyze single files, multiple files, or entire directories

### Real-Time Tail Monitoring
- **`--tail` mode** — watch log files and see new entries printed as they arrive
- **Color-coded output** — levels colorized for quick visual scanning (ANSI terminals)
- **Live summary** — per-session stats printed on Ctrl+C
- **Multi-file tail** — watch multiple files or directories simultaneously

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

Or with development dependencies:

```bash
pip install -e ".[dev]"
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

# Real-time tail mode (watch files live)
logpulse /var/log/app.log --tail

# Tail with filtering (only ERROR+ from specific source)
logpulse /var/log/app.log --tail -l ERROR -s server.api

# Tail a directory of logs
logpulse /var/log/ --tail --no-color
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

### Real-Time Tail API

```python
from logpulse.report import tail_log, LiveDashboard

# Watch a file and process entries as they appear
for entry in tail_log("/var/log/app.log"):
    print(f"[{entry.level}] {entry.message}")

# Use the built-in color-coded dashboard
dashboard = LiveDashboard()
for entry in tail_log("/var/log/app.log", callback=dashboard.on_entry):
    pass  # entries are printed automatically

dashboard.print_summary()  # call on exit
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

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Check formatting
ruff format --check .

# Auto-format
ruff format .

# Lint
ruff check .
```

## CI/CD

GitHub Actions runs on every push and PR:
- **Lint** — ruff format + lint check
- **Test** — pytest on Python 3.10, 3.11, 3.12
- **Build** — sdist + wheel build

## Benchmarks

See [benchmarks/README.md](benchmarks/README.md) for performance data.

```bash
python benchmarks/run_benchmarks.py
```

## Project Structure

```
LogPulse/
├── logpulse/
│   ├── __init__.py          # Package metadata
│   ├── parser.py            # Log line parsing (6 formats)
│   ├── filter.py            # Filtering engine
│   ├── report.py            # Report generation + real-time tail + dashboard
│   ├── analyzer.py          # Main analyzer orchestrator
│   └── cli.py               # CLI interface (--tail mode)
├── tests/
│   └── test_all.py          # 28 unit tests
├── benchmarks/
│   ├── README.md            # Performance data
│   └── run_benchmarks.py    # Benchmark runner
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI
├── pyproject.toml           # Modern Python packaging
├── setup.py                 # Legacy packaging (deprecated)
├── .gitignore
└── README.md
```

## License

MIT
