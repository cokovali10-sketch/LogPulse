"""Log line parsing for common log formats."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}

SYSLOG_PATTERN = re.compile(
    r"^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<program>\S+?)(?:\[(?P<pid>\d+)\])?:\s+(?P<message>.+)$"
)

COMMON_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"
    r"(?P<source>\S+)\s*[-:]?\s*(?P<message>.+)$"
)

APACHE_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+(?P<user>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\d+|-)'
    r'(?:\s+"(?P<referrer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
)

NGINX_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+-\s+(?P<user>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\d+|-)\s+'
    r'"(?P<referrer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
    r'(?:\s+"(?P<forwarded>[^"]*)")?'
    r'(?:\s+(?P<request_time>[\d.]+))?'
)

WINDOWS_EVENT_PATTERN = re.compile(
    r'^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
    r'(?P<level>Information|Warning|Error|Critical)\s+'
    r'(?P<source>[^-]+)\s+-\s+(?P<message>.+)$'
)

# Paper / Purpur / Spigot console: [12:43:22] [Server thread/ERROR]: message
PAPER_PATTERN = re.compile(
    r"^\[(?P<timestamp>\d{2}:\d{2}:\d{2})\]\s+"
    r"\[(?P<source>[^\]]*?)/(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|ERR|CRITICAL|FATAL)\]:\s*"
    r"(?P<message>.+)$"
)

# Paper short form: [12:43:22 INFO]: message
PAPER_SHORT_PATTERN = re.compile(
    r"^\[(?P<timestamp>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|ERR|CRITICAL|FATAL)\]:\s*"
    r"(?P<message>.+)$"
)

LEVEL_ALIASES = {
    "WARN": "WARNING",
    "ERR": "ERROR",
    "FATAL": "CRITICAL",
}

GENERIC_BRACKETED = re.compile(
    r'^(?:\[?(?P<timestamp>[^\]\s]+(?:\s+[^\]]+)?)\]?\s+)?'
    r'(?P<level>DEBUG|INFO|NOTICE|WARNING|WARN|ERROR|ERR|CRITICAL|FATAL|ALERT|EMERG)\s*'
    r'(?::?\s+)?(?P<message>.+)$'
)

JSON_LINE_KEYS = {"timestamp", "level", "message"}


@dataclass
class LogEntry:
    timestamp: Optional[datetime]
    level: str
    source: str
    message: str
    line_number: int
    raw: str
    extra: dict

    @property
    def level_num(self) -> int:
        return LEVELS.get(self.level.upper(), 0)


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%b %d %H:%M:%S",
        "%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def parse_log_line(raw: str, line_number: int) -> Optional[LogEntry]:
    raw = raw.rstrip("\n\r")
    if not raw.strip():
        return None

    m = COMMON_PATTERN.match(raw)
    if m:
        return LogEntry(
            timestamp=parse_timestamp(m.group("timestamp")),
            level=m.group("level").upper(),
            source=m.group("source"),
            message=m.group("message"),
            line_number=line_number,
            raw=raw,
            extra={},
        )

    m = PAPER_PATTERN.match(raw)
    if not m:
        m = PAPER_SHORT_PATTERN.match(raw)
    if m:
        return LogEntry(
            timestamp=parse_timestamp(m.group("timestamp")),
            level=LEVEL_ALIASES.get(m.group("level"), m.group("level")),
            source=m.groupdict().get("source") or "unknown",
            message=m.group("message"),
            line_number=line_number,
            raw=raw,
            extra={"format": "paper"},
        )

    m = SYSLOG_PATTERN.match(raw)
    if m:
        return LogEntry(
            timestamp=parse_timestamp(m.group("timestamp")),
            level="INFO",
            source=m.group("program"),
            message=m.group("message"),
            line_number=line_number,
            raw=raw,
            extra={"host": m.group("host"), "pid": m.group("pid")},
        )

    m = APACHE_PATTERN.match(raw)
    if m:
        level = "ERROR" if int(m.group("status")) >= 400 else "INFO"
        return LogEntry(
            timestamp=parse_timestamp(m.group("timestamp")),
            level=level,
            source=m.group("ip"),
            message=f'{m.group("method")} {m.group("path")} -> {m.group("status")}',
            line_number=line_number,
            raw=raw,
            extra={
                "method": m.group("method"),
                "path": m.group("path"),
                "status": int(m.group("status")),
                "size": m.group("size"),
                "user_agent": m.group("user_agent"),
                "referrer": m.group("referrer"),
            },
        )

    m = NGINX_PATTERN.match(raw)
    if m:
        status = int(m.group("status"))
        level = "ERROR" if status >= 500 else ("WARNING" if status >= 400 else "INFO")
        extra = {
            "method": m.group("method"),
            "path": m.group("path"),
            "status": status,
            "size": m.group("size"),
            "user_agent": m.group("user_agent"),
            "referrer": m.group("referrer"),
            "forwarded": m.group("forwarded"),
        }
        if m.group("request_time"):
            extra["request_time"] = float(m.group("request_time"))
        return LogEntry(
            timestamp=parse_timestamp(m.group("timestamp")),
            level=level,
            source=m.group("ip"),
            message=f'{m.group("method")} {m.group("path")} -> {status}',
            line_number=line_number,
            raw=raw,
            extra=extra,
        )

    m = WINDOWS_EVENT_PATTERN.match(raw)
    if m:
        level_map = {
            "Information": "INFO", "Warning": "WARNING",
            "Error": "ERROR", "Critical": "CRITICAL",
        }
        return LogEntry(
            timestamp=parse_timestamp(f"{m.group('date')} {m.group('time')}"),
            level=level_map.get(m.group("level"), "INFO"),
            source=m.group("source").strip(),
            message=m.group("message"),
            line_number=line_number,
            raw=raw,
            extra={"event_level": m.group("level")},
        )

    try:
        import json
        data = json.loads(raw)
        if isinstance(data, dict) and JSON_LINE_KEYS.issubset(data.keys()):
            return LogEntry(
                timestamp=parse_timestamp(str(data.get("timestamp", ""))),
                level=str(data.get("level", "INFO")).upper(),
                source=str(data.get("source", "unknown")),
                message=str(data.get("message", "")),
                line_number=line_number,
                raw=raw,
                extra={k: v for k, v in data.items() if k not in JSON_LINE_KEYS},
            )
    except Exception:
        pass

    return LogEntry(
        timestamp=None,
        level="INFO",
        source="unknown",
        message=raw,
        line_number=line_number,
        raw=raw,
        extra={},
    )
