"""
Core analysis engine for Commit Archaeologist.

Walks a git repository's commit history and produces structured statistics:
- file "hotspots" (files changed most often / with most churn)
- contributor activity
- commit timing patterns (busiest days / hours)
- streaks and gaps in commit history
- basic commit-message quality signals
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError


LAZY_MESSAGE_PATTERNS = [
    r"^wip$",
    r"^fix$",
    r"^fixes$",
    r"^fix stuff$",
    r"^stuff$",
    r"^asdf+$",
    r"^update$",
    r"^updates$",
    r"^changes$",
    r"^minor changes$",
    r"^final$",
   r"^final$",
    r"^final v?\d+$",
    r"^\.+$",
    r"^test$",
    r"^temp$",
    r"^tmp$",
    r"^oops$",
    r"^\s*$",
]
LAZY_RE = re.compile("|".join(LAZY_MESSAGE_PATTERNS), re.IGNORECASE)


@dataclass
class FileStat:
    path: str
    commit_count: int = 0
    insertions: int = 0
    deletions: int = 0
    authors: set = field(default_factory=set)
    last_modified: Optional[datetime] = None

    @property
    def churn(self) -> int:
        return self.insertions + self.deletions


@dataclass
class AuthorStat:
    name: str
    commit_count: int = 0
    insertions: int = 0
    deletions: int = 0
    files_touched: set = field(default_factory=set)
    first_commit: Optional[datetime] = None
    last_commit: Optional[datetime] = None


@dataclass
class AnalysisResult:
    repo_path: str
    total_commits: int = 0
 date_range: Optional[tuple] = None
    file_stats: dict = field(default_factory=dict)
    author_stats: dict = field(default_factory=dict)
    weekday_counts: Counter = field(default_factory=Counter)
    hour_counts: Counter = field(default_factory=Counter)
    lazy_messages: list = field(default_factory=list)
    longest_gap: Optional[timedelta] = None
    longest_gap_dates: Optional[tuple] = None
    longest_streak_days: int = 0

    def top_hotspots(self, n: int = 10):
        return sorted(
            self.file_stats.values(), key=lambda f: (f.commit_count, f.churn), reverse=True
        )[:n]

    def top_churn(self, n: int = 10):
        return sorted(self.file_stats.values(), key=lambda f: f.churn, reverse=True)[:n]

    def top_authors(self, n: int = 10):
        return sorted(
            self.author_stats.values(), key=lambda a: a.commit_count, reverse=True
        )[:n]

    def busiest_weekday(self):
        if not self.weekday_counts:
            return None
        return self.weekday_counts.most_common(1)[0]

    def busiest_hour(self):
        if not self.hour_counts:
            return None
        return self.hour_counts.most_common(1)[0]


def analyze_repo(
    repo_path: str,
    since: Optional[str] = None,
    max_commits: Optional[int] = None,
) -> AnalysisResult:
    """
    Analyze a git repository and return an AnalysisResult.

    :param repo_path: path to the local git repository
    :param since: optional date string (e.g. "2024-01-01") to limit history
    :param max_commits: optional cap on number of commits walked (most recent first)
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        raise ValueError(f"'{repo_path}' is not a valid git repository") from e

    if repo.bare:
        raise ValueError(f"'{repo_path}' is a bare repository with no working history")

    kwargs = {}
    if since:
        kwargs["since"] = since
    if max_commits:
        kwargs["max_count"] = max_commits

    result = AnalysisResult(repo_path=repo_path)

    try:
        commits = list(repo.iter_commits(**kwargs))
    except ValueError:
        # Repository has no commits yet (no HEAD reference)
        commits = []

    commits.reverse()  # oldest first, for streak/gap calculations
    result.total_commits = len(commits)

    if not commits:
        return result

    result.date_range = (
        datetime.fromtimestamp(commits[0].committed_date),
        datetime.fromtimestamp(commits[-1].committed_date),
    )

    commit_dates = []

    for commit in commits:
        dt = datetime.fromtimestamp(commit.committed_date)
        commit_dates.append(dt)
        author_name = commit.author.name or "Unknown"
        message_first_line = commit.message.strip().splitlines()[0] if commit.message.strip() else ""

        result.weekday_counts[dt.strftime("%A")] += 1
        result.hour_counts[dt.hour] += 1

        if LAZY_RE.match(message_first_line.strip()):
            result.lazy_messages.append(
                {"sha": commit.hexsha[:7], "message": message_first_line, "date": dt}
            )

        astat = result.author_stats.setdefault(author_name, AuthorStat(name=author_name))
        astat.commit_count += 1
        if astat.first_commit is None or dt < astat.first_commit:
            astat.first_commit = dt
        if astat.last_commit is None or dt > astat.last_commit:
            astat.last_commit = dt
try:
            stats = commit.stats
        except (ValueError, UnicodeDecodeError) as e:
            # Some commits (e.g. certain merges, or bad encodings) can't produce stats.
            # Skip just this commit's file/insertion data, not the whole analysis.
            continue

        astat.insertions += stats.total.get("insertions", 0)
        astat.deletions += stats.total.get("deletions", 0)

        for filepath, filestats in stats.files.items():
            fstat = result.file_stats.setdefault(filepath, FileStat(path=filepath))
            fstat.commit_count += 1
            fstat.insertions += filestats.get("insertions", 0)
            fstat.deletions += filestats.get("deletions", 0)
            fstat.authors.add(author_name)
            if fstat.last_modified is None or dt > fstat.last_modified:
                fstat.last_modified = dt
            astat.files_touched.add(filepath)

    # Gaps and streaks (by calendar day)
    unique_days = sorted({d.date() for d in commit_dates})
    if len(unique_days) > 1:
        longest_gap = timedelta(0)
        gap_dates = None
        for a, b in zip(unique_days, unique_days[1:]):
            gap = b - a
            if gap > longest_gap:
                longest_gap = gap
                gap_dates = (a, b)
        result.longest_gap = longest_gap
        result.longest_gap_dates = gap_dates

        longest_streak = 1
        current_streak = 1
        for a, b in zip(unique_days, unique_days[1:]):
            if (b - a).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        result.longest_streak_days = longest_streak
    elif len(unique_days) == 1:
        result.longest_streak_days = 1

    return result
