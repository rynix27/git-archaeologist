# Commit Archaeologist

Dig through a git repository's commit history and unearth its story.

Commit Archaeologist analyzes any local git repo and tells you things your `git log` never will:
which files are **hotspots** that keep getting rewritten, who the biggest contributors are, when
your team actually works, and how sloppy your commit messages have secretly been.

```
╭────────────────────────────────────╮
│ Commit Archaeologist               │
│ .                                  │
│ 214 commits  2023-01-04 → 2026-07-06│
╰────────────────────────────────────╯

The Story So Far
Over 913 days, this repo saw 214 commits from 4 contributors. Alice led the
charge with 121 commits (56% of all activity). The most contested files were
src/api/routes.py, src/db/models.py, tests/test_api.py — these got rewritten
again and again, which usually means core logic, shared utilities, or a spot
that keeps causing headaches...
```

## Features

- **File hotspot detection** — finds the files with the most commits and churn (insertion + deletion volume), a strong signal for where bugs cluster or refactors are overdue
- **Contributor breakdown** — commits, insertions, deletions, and files touched per author
- **Commit rhythm analysis** — busiest weekday/hour, ascii bar chart of activity by day of week
- **Streaks & gaps** — longest consecutive commit streak, longest quiet spell
- **Lazy commit message detection** — flags messages like `wip`, `fix`, `asdf`, `final_v2` etc.
- **Auto-generated narrative summary** — a plain-English "story" of the repo's history
- **Markdown export** — save a shareable report alongside your project

## Installation

```bash
git clone <your-repo-url>
cd commit-archaeologist
pip install -e .
```

Requires Python 3.9+.

## Usage

```bash
# Analyze the current directory
git-archaeologist

# Analyze a specific repo
git-archaeologist /path/to/other/repo

# Only look at recent history
git-archaeologist . --since 2025-01-01

# Limit to the last 500 commits
git-archaeologist . --max-commits 500

# Show top 20 in each ranked list instead of the default 10
git-archaeologist . --top 20

# Export a Markdown report
git-archaeologist . --export report.md
```

## How it works

Commit Archaeologist uses [GitPython](https://gitpython.readthedocs.io/) to walk a repository's
commit history, aggregating per-file and per-author statistics as it goes. Weekday/hour counts are
tallied per commit timestamp, and streak/gap detection works off the set of unique calendar days
with at least one commit. None of this touches the network or requires any external service —
it's a pure, local analysis of `.git`.

## Development

```bash
pip install -r requirements.txt pytest
pytest tests/ -v
```

## Ideas for extending this

- Render the commit-rhythm heatmap as an actual image (matplotlib) instead of ascii bars
- Add a `--html` export with a nicer visual report
- Detect "bus factor" — files owned almost entirely by one author who could leave
- Blame-based hotspot detection (which *lines*, not just files, are most contested)
- GitHub Action that posts a weekly digest as a repo comment

## License

MIT — see [LICENSE](LICENSE).
