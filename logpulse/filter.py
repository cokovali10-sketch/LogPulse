"""Log filtering by level, source, time range, regex, and keywords."""

import re
from datetime import datetime
from typing import Callable, List, Optional

from .parser import LogEntry


class LogFilter:
    def __init__(self):
        self._filters: List[Callable[[LogEntry], bool]] = []

    def by_level(self, min_level: str = "DEBUG", max_level: str = "CRITICAL") -> "LogFilter":
        from .parser import LEVELS
        min_n = LEVELS.get(min_level.upper(), 0)
        max_n = LEVELS.get(max_level.upper(), 4)
        self._filters.append(lambda e: min_n <= e.level_num <= max_n)
        return self

    def by_source(self, *sources: str) -> "LogFilter":
        src_set = {s.lower() for s in sources}
        self._filters.append(lambda e: e.source.lower() in src_set)
        return self

    def by_time_range(self, start: Optional[datetime] = None, end: Optional[datetime] = None) -> "LogFilter":
        def check(entry: LogEntry) -> bool:
            if entry.timestamp is None:
                return True
            if start and entry.timestamp < start:
                return False
            if end and entry.timestamp > end:
                return False
            return True
        self._filters.append(check)
        return self

    def by_regex(self, pattern: str, field: str = "message") -> "LogFilter":
        compiled = re.compile(pattern, re.IGNORECASE)
        def check(entry: LogEntry) -> bool:
            text = getattr(entry, field, entry.message)
            return bool(compiled.search(str(text)))
        self._filters.append(check)
        return self

    def by_keyword(self, *keywords: str) -> "LogFilter":
        kw_lower = [k.lower() for k in keywords]
        self._filters.append(
            lambda e: any(kw in e.message.lower() for kw in kw_lower)
        )
        return self

    def exclude_level(self, level: str) -> "LogFilter":
        from .parser import LEVELS
        level_n = LEVELS.get(level.upper(), 0)
        self._filters.append(lambda e: e.level_num != level_n)
        return self

    def custom(self, fn: Callable[[LogEntry], bool]) -> "LogFilter":
        self._filters.append(fn)
        return self

    def apply(self, entries: List[LogEntry]) -> List[LogEntry]:
        result = entries
        for f in self._filters:
            result = [e for e in result if f(e)]
        return result

    def reset(self) -> "LogFilter":
        self._filters.clear()
        return self
