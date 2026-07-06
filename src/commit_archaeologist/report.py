"""
Rendering layer for Commit Archaeologist.

Turns an AnalysisResult into:
- a rich terminal report (tables, panels, a simple ascii heatmap)
- a narrative summary (plain-language "story" of the repo)
- a markdown export suitable for saving alongside a project
"""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .analyzer import AnalysisResult

WEEKDAY_ORDER = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def build_narrative(result: AnalysisResult) -> str:
    if result.total_commits == 0:
        return "This repository has no commit history to analyze yet."

    start, end = result.date_range
    span_days = max((end - start).days, 1)
    lines = []

    lines.append(
        f"Over {span_days} day{'s' if span_days != 1 else ''} "
        f"(from {_fmt_date(start)} to {_fmt_date(end)}), this repo saw "
        f"{result.total_commits} commit{'s' if result.total_commits != 1 else ''} "
        f"from {len(result.author_stats)} contributor{'s' if len(result.author_stats) != 1 else ''}."
    )

    top_author = result.top_authors(1)
    if top_author:
        a = top_author[0]
        share = (a.commit_count / result.total_commits) * 100
        lines.append(
            f"{a.name} led the charge with {a.commit_count} commits ({share:.0f}% of all activity)."
        )

    hotspots = result.top_hotspots(3)
    if hotspots:
        names = ", ".join(f.path for f in hotspots)
        lines.append(
            f"The most contested files were {names} — these got rewritten again and again, "
            "which usually means core logic, shared utilities, or a spot that keeps causing headaches."
        )

    weekday = result.busiest_weekday()
    hour = result.busiest_hour()
    if weekday and hour:
        lines.append(
            f"Most commits landed on {weekday[0]}s, and the busiest hour of the day was "
            f"{hour[0]:02d}:00 — draw your own conclusions about work-life balance."
        )

    if result.longest_streak_days > 1:
        lines.append(
            f"The longest consecutive commit streak was {result.longest_streak_days} days."
        )
    if result.longest_gap and result.longest_gap.days > 0:
        g0, g1 = result.longest_gap_dates
        lines.append(
            f"The longest quiet spell lasted {result.longest_gap.days} days, "
            f"between {g0} and {g1} — a vacation, a pivot, or just life happening."
        )

    if result.lazy_messages:
        lines.append(
            f"{len(result.lazy_messages)} commit message(s) were, let's say, low on detail "
            f"(e.g. \"{result.lazy_messages[0]['message']}\") — future-you will not thank present-you."
        )

    return " ".join(lines)


def render_terminal_report(result: AnalysisResult, console: Console | None = None, top_n: int = 10) -> None:
    console = console or Console()

    if result.total_commits == 0:
        console.print(Panel("No commits found in this repository.", title="Commit Archaeologist"))
        return

    start, end = result.date_range
    header = Text()
    header.append("Commit Archaeologist\n", style="bold cyan")
    header.append(f"{result.repo_path}\n", style="dim")
    header.append(f"{result.total_commits} commits  ", style="bold")
    header.append(f"{_fmt_date(start)} → {_fmt_date(end)}", style="dim")
    console.print(Panel(header, expand=False))

    console.print("\n[bold]The Story So Far[/bold]")
    console.print(build_narrative(result), style="italic")

    console.print("\n[bold]File Hotspots[/bold] (most frequently changed)")
    table = Table()
    table.add_column("File")
    table.add_column("Commits", justify="right")
    table.add_column("Churn (+/-)", justify="right")
    table.add_column("Authors", justify="right")
    for f in result.top_hotspots(top_n):
        table.add_row(f.path, str(f.commit_count), f"+{f.insertions}/-{f.deletions}", str(len(f.authors)))
    console.print(table)

    console.print("\n[bold]Contributors[/bold]")
    table = Table()
    table.add_column("Author")
    table.add_column("Commits", justify="right")
    table.add_column("Insertions", justify="right")
    table.add_column("Deletions", justify="right")
    table.add_column("Files Touched", justify="right")
    for a in result.top_authors(top_n):
        table.add_row(a.name, str(a.commit_count), f"+{a.insertions}", f"-{a.deletions}", str(len(a.files_touched)))
    console.print(table)

    console.print("\n[bold]Commit Rhythm[/bold]")
  max_count = max(result.weekday_counts.values()) if result.weekday_counts else 1
    for day in WEEKDAY_ORDER:
        count = result.weekday_counts.get(day, 0)
        bar_len = int((count / max_count) * 30) if max_count else 0
        bar = "█" * bar_len
        console.print(f"  {day:<10} {bar} {count}")

    if result.lazy_messages:
        console.print(f"\n[bold]Lazy Commit Messages[/bold] ({len(result.lazy_messages)} found)")
        for m in result.lazy_messages[:5]:
            console.print(f"  [dim]{m['sha']}[/dim]  \"{m['message']}\"  ({_fmt_date(m['date'])})")
        if len(result.lazy_messages) > 5:
            console.print(f"  ...and {len(result.lazy_messages) - 5} more")

    console.print()


def render_markdown_report(result: AnalysisResult, top_n: int = 10) -> str:
    if result.total_commits == 0:
        return "# Commit Archaeologist Report\n\nNo commits found in this repository.\n"

    start, end = result.date_range
    lines = [
        "# Commit Archaeologist Report",
        "",
        f"**Repository:** `{result.repo_path}`  ",
        f"**Commits analyzed:** {result.total_commits}  ",
        f"**Date range:** {_fmt_date(start)} → {_fmt_date(end)}",
        "",
        "## The Story So Far",
        "",
        build_narrative(result),
        "",
        "## File Hotspots",
        "",
        "| File | Commits | Churn | Authors |",
        "|---|---|---|---|",
    ]
    for f in result.top_hotspots(top_n):
        lines.append(f"| `{f.path}` | {f.commit_count} | +{f.insertions}/-{f.deletions} | {len(f.authors)} |")

    lines += [
        "",
        "## Contributors",
        "",
        "| Author | Commits | Insertions | Deletions | Files Touched |",
        "|---|---|---|---|---|",
    ]
    for a in result.top_authors(top_n):
        lines.append(
            f"| {a.name} | {a.commit_count} | +{a.insertions} | -{a.deletions} | {len(a.files_touched)} |"
        )

    lines += ["", "## Commit Rhythm", ""]
 max_count = max(result.weekday_counts.values()) if result.weekday_counts else 1
    for day in WEEKDAY_ORDER:
        count = result.weekday_counts.get(day, 0)
        bar_len = int((count / max_count) * 30) if max_count else 0
        lines.append(f"- {day:<10} {'█' * bar_len} {count}")

    if result.lazy_messages:
        lines += ["", f"## Lazy Commit Messages ({len(result.lazy_messages)} found)", ""]
        for m in result.lazy_messages:
            lines.append(f"- `{m['sha']}` \"{m['message']}\" ({_fmt_date(m['date'])})")

    lines.append("")
    return "\n".join(lines)
