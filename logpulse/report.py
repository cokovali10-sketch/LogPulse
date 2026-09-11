"""Report generation from filtered log entries and real-time tail monitoring."""

import json
import csv
import io
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable, Dict, List, Optional

from .parser import LogEntry, parse_log_line


@dataclass
class LevelStats:
    count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


@dataclass
class SourceStats:
    total: int = 0
    levels: Dict[str, int] = field(default_factory=dict)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


@dataclass
class Report:
    total_lines: int
    filtered_lines: int
    time_range: Optional[str]
    level_counts: Dict[str, int]
    source_counts: Dict[str, int]
    hourly_distribution: Dict[int, int]
    top_messages: List[Dict[str, int]]
    source_details: Dict[str, dict]
    errors_by_source: Dict[str, List[dict]]
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


class ReportGenerator:
    def __init__(self, entries: List[LogEntry], total_lines: int = 0):
        self.entries = entries
        self.total_lines = total_lines

    def generate(self) -> Report:
        level_counts = Counter(e.level for e in self.entries)
        source_counts = Counter(e.source for e in self.entries)

        hourly: Dict[int, int] = defaultdict(int)
        for e in self.entries:
            if e.timestamp:
                hourly[e.timestamp.hour] += 1

        msg_counts = Counter(e.message[:100] for e in self.entries)
        top_messages = [{"message": m, "count": c} for m, c in msg_counts.most_common(20)]

        source_details: Dict[str, SourceStats] = {}
        for src in source_counts:
            src_entries = [e for e in self.entries if e.source == src]
            timestamps = [e.timestamp for e in src_entries if e.timestamp]
            sd = SourceStats(
                total=len(src_entries),
                levels=dict(Counter(e.level for e in src_entries)),
                first_seen=str(min(timestamps)) if timestamps else None,
                last_seen=str(max(timestamps)) if timestamps else None,
            )
            source_details[src] = asdict(sd)

        errors_by_source: Dict[str, List[dict]] = defaultdict(list)
        for e in self.entries:
            if e.level in ("ERROR", "CRITICAL"):
                errors_by_source[e.source].append({
                    "line": e.line_number,
                    "message": e.message[:200],
                    "timestamp": str(e.timestamp) if e.timestamp else None,
                })

        timestamps = [e.timestamp for e in self.entries if e.timestamp]
        time_range = None
        if timestamps:
            time_range = f"{min(timestamps)} -> {max(timestamps)}"

        return Report(
            total_lines=self.total_lines,
            filtered_lines=len(self.entries),
            time_range=time_range,
            level_counts=dict(level_counts),
            source_counts=dict(source_counts),
            hourly_distribution=dict(sorted(hourly.items())),
            top_messages=top_messages,
            source_details=source_details,
            errors_by_source=dict(errors_by_source),
        )

    def to_text(self) -> str:
        r = self.generate()
        lines = [
            "=" * 60,
            "  LogPulse Report",
            "=" * 60,
            f"Generated:    {r.generated_at}",
            f"Total lines:  {r.total_lines}",
            f"Shown lines:  {r.filtered_lines}",
            f"Time range:   {r.time_range or 'N/A'}",
            "",
            "--- Level Distribution ---",
        ]
        for level, count in sorted(r.level_counts.items()):
            bar = "#" * min(count, 50)
            lines.append(f"  {level:10s} {count:6d}  {bar}")

        lines.extend(["", "--- Source Distribution ---"])
        for src, count in sorted(r.source_counts.items(), key=lambda x: -x[1])[:20]:
            lines.append(f"  {src:30s} {count:6d}")

        if r.hourly_distribution:
            lines.extend(["", "--- Hourly Distribution ---"])
            max_h = max(r.hourly_distribution.values()) or 1
            for hour in range(24):
                cnt = r.hourly_distribution.get(hour, 0)
                bar = "#" * int(cnt / max_h * 40) if cnt else ""
                lines.append(f"  {hour:02d}:00  {cnt:5d}  {bar}")

        if r.errors_by_source:
            lines.extend(["", "--- Errors (first 5 per source) ---"])
            for src, errors in r.errors_by_source.items():
                lines.append(f"  [{src}]")
                for err in errors[:5]:
                    lines.append(f"    L{err['line']}: {err['message'][:80]}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self.generate()), indent=indent, default=str)

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["line", "timestamp", "level", "source", "message"])
        for e in self.entries:
            writer.writerow([
                e.line_number,
                str(e.timestamp) if e.timestamp else "",
                e.level,
                e.source,
                e.message[:200],
            ])
        return buf.getvalue()

    def to_html(self) -> str:
        r = self.generate()
        html = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<title>LogPulse Report</title>",
            "<style>",
            "body{font-family:monospace;background:#0d1117;color:#c9d1d9;margin:2em;}",
            "h1{color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:.5em;}",
            "table{border-collapse:collapse;width:100%;margin:1em 0;}",
            "th,td{border:1px solid #30363d;padding:8px 12px;text-align:left;}",
            "th{background:#161b22;color:#58a6ff;}",
            ".error{color:#f85149;}.warn{color:#d29922;}.info{color:#c9d1d9;}",
            "</style></head><body>",
            f"<h1>LogPulse Report</h1>",
            f"<p>Generated: {r.generated_at}<br>",
            f"Total: {r.total_lines} lines | Shown: {r.filtered_lines} lines<br>",
            f"Time range: {r.time_range or 'N/A'}</p>",
        ]

        html.append("<h2>Levels</h2><table><tr><th>Level</th><th>Count</th></tr>")
        for lvl, cnt in sorted(r.level_counts.items()):
            cls = lvl.lower()
            html.append(f'<tr><td class="{cls}">{lvl}</td><td>{cnt}</td></tr>')
        html.append("</table>")

        html.append("<h2>Top Sources</h2><table><tr><th>Source</th><th>Count</th></tr>")
        for src, cnt in sorted(r.source_counts.items(), key=lambda x: -x[1])[:20]:
            html.append(f"<tr><td>{src}</td><td>{cnt}</td></tr>")
        html.append("</table>")

        if r.errors_by_source:
            html.append("<h2>Errors</h2>")
            for src, errors in r.errors_by_source.items():
                html.append(f"<h3>{src}</h3><ul>")
                for err in errors[:10]:
                    html.append(f"<li>L{err['line']}: {err['message'][:100]}</li>")
                html.append("</ul>")

        html.append("</body></html>")
        return "\n".join(html)


def tail_log(
    filepath: str,
    callback: Optional[Callable[[LogEntry], None]] = None,
    poll_interval: float = 0.5,
    follow: bool = True,
):
    """Watch a log file and yield new lines as they appear.

    Args:
        filepath: Path to the log file to tail.
        callback: Optional function called for each new parsed LogEntry.
        poll_interval: Seconds between polls when waiting for new data.
        follow: If True, keep watching after reaching EOF. If False, stop at EOF.

    Yields:
        LogEntry objects as new lines are read from the file.
    """
    line_number = 0
    while not os.path.isfile(filepath):
        time.sleep(poll_interval)

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        while True:
            line = f.readline()
            if line:
                line_number += 1
                entry = parse_log_line(line, line_number)
                if entry:
                    if callback:
                        callback(entry)
                    yield entry
            elif follow:
                time.sleep(poll_interval)
            else:
                break


class LiveDashboard:
    """Color-coded real-time terminal dashboard for log monitoring.

    ANSI color codes are used for level-based coloring. Falls back to plain
    text when the terminal does not support color.
    """

    COLORS = {
        "DEBUG": "\033[36m",      # cyan
        "INFO": "\033[37m",       # white
        "WARNING": "\033[33m",    # yellow
        "ERROR": "\033[31m",      # red
        "CRITICAL": "\033[1;31m", # bold red
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, use_color: Optional[bool] = None, max_display: int = 50):
        if use_color is None:
            self._color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        else:
            self._color = use_color
        self.max_display = max_display
        self._count = 0
        self._level_counts: Dict[str, int] = Counter()

    def _colorize(self, level: str, text: str) -> str:
        if not self._color:
            return text
        code = self.COLORS.get(level, "")
        return f"{code}{text}{self.RESET}"

    def on_entry(self, entry: LogEntry) -> None:
        """Handle a new log entry — print it to stdout."""
        self._count += 1
        self._level_counts[entry.level] += 1

        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
        level_tag = self._colorize(entry.level, f"[{entry.level:>8s}]")
        source_tag = self._colorize(entry.level, f" {entry.source}")

        line = f"{ts} {level_tag}{source_tag}  {entry.message}"
        print(line, flush=True)

    def print_summary(self) -> None:
        """Print a summary of the monitoring session."""
        print()
        print("=" * 60)
        print(f"  {self.BOLD}LogPulse Live Summary{self.RESET}")
        print("=" * 60)
        print(f"  Total entries seen: {self._count}")
        print()
        if self._level_counts:
            print("  Level breakdown:")
            for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                cnt = self._level_counts.get(level, 0)
                if cnt:
                    bar = "#" * min(cnt, 40)
                    print(f"    {level:10s} {cnt:6d}  {bar}")
        print("=" * 60)
