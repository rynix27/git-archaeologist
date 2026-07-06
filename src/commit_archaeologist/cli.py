"""
Command-line interface for Commit Archaeologist.
"""

from __future__ import annotations

import sys

import click
from rich.console import Console

from .analyzer import analyze_repo
from .report import render_terminal_report, render_markdown_report


@click.command()
@click.argument("repo_path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--since", default=None, help="Only analyze commits since this date, e.g. 2024-01-01")
@click.option("--max-commits", default=None, type=int, help="Limit analysis to the N most recent commits")
@click.option("--top", "top_n", default=10, type=int, help="Number of items to show in each ranked list")
@click.option(
    "--export",
    "export_path",
    default=None,
    type=click.Path(),
    help="Write a Markdown report to this file path",
)
def main(repo_path: str, since: str | None, max_commits: int | None, top_n: int, export_path: str | None):
    """
    Dig through a git repository's history and unearth its story.

    REPO_PATH defaults to the current directory.
    """
    console = Console()

   try:
        with console.status("[bold cyan]Digging through commit history..."):
            result = analyze_repo(repo_path, since=since, max_commits=max_commits)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)

    render_terminal_report(result, console=console, top_n=top_n)

    if export_path:
        markdown = render_markdown_report(result, top_n=top_n)
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        console.print(f"[green]Report exported to {export_path}[/green]")


if __name__ == "__main__":
    main()
