"""Main analyzer — load files, parse, filter, report."""

import os
from datetime import datetime
from typing import List, Optional

from .parser import LogEntry, parse_log_line
from .filter import LogFilter
from .report import Report, ReportGenerator


class LogAnalyzer:
    def __init__(self):
        self.entries: List[LogEntry] = []
        self.total_lines: int = 0
        self._files_loaded: List[str] = []

    def load_file(self, filepath: str) -> int:
        count = 0
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                entry = parse_log_line(line, self.total_lines + i)
                if entry:
                    self.entries.append(entry)
                    count += 1
        self.total_lines += count
        self._files_loaded.append(filepath)
        return count

    def load_directory(self, dirpath: str, extensions: Optional[List[str]] = None) -> int:
        if extensions is None:
            extensions = [".log", ".txt", ".out", ".err"]
        count = 0
        for root, _dirs, files in os.walk(dirpath):
            for fname in sorted(files):
                if any(fname.endswith(ext) for ext in extensions):
                    fpath = os.path.join(root, fname)
                    count += self.load_file(fpath)
        return count

    def load_string(self, text: str) -> int:
        count = 0
        for i, line in enumerate(text.splitlines(), 1):
            entry = parse_log_line(line, self.total_lines + i)
            if entry:
                self.entries.append(entry)
                count += 1
        self.total_lines += count
        return count

    def filter(self) -> LogFilter:
        return LogFilter()

    def apply_filter(self, log_filter: LogFilter) -> "LogAnalyzer":
        filtered = LogAnalyzer()
        filtered.entries = log_filter.apply(self.entries)
        filtered.total_lines = self.total_lines
        filtered._files_loaded = self._files_loaded.copy()
        return filtered

    def report(self) -> ReportGenerator:
        return ReportGenerator(self.entries, self.total_lines)

    @property
    def stats(self) -> dict:
        from collections import Counter
        levels = Counter(e.level for e in self.entries)
        sources = Counter(e.source for e in self.entries)
        return {
            "total_entries": len(self.entries),
            "levels": dict(levels),
            "top_sources": dict(sources.most_common(10)),
            "files_loaded": self._files_loaded,
        }
