"""
Basic tests for the analyzer, using a throwaway git repo built at test time.
"""

import subprocess
import time
from pathlib import Path

import pytest

from commit_archaeologist.analyzer import analyze_repo


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def sample_repo(tmp_path):
    repo_dir = tmp_path / "sample"
    repo_dir.mkdir()
    run(["git", "init", "-q"], cwd=repo_dir)
    run(["git", "config", "user.email", "a@example.com"], cwd=repo_dir)
    run(["git", "config", "user.name", "Alice"], cwd=repo_dir)

    (repo_dir / "core.py").write_text("print('v1')\n")
    run(["git", "add", "."], cwd=repo_dir)
    run(["git", "commit", "-q", "-m", "Initial commit"], cwd=repo_dir)

    (repo_dir / "core.py").write_text("print('v2')\n")
    run(["git", "add", "."], cwd=repo_dir)
    run(["git", "commit", "-q", "-m", "wip"], cwd=repo_dir)

    (repo_dir / "utils.py").write_text("def helper(): pass\n")
    run(["git", "add", "."], cwd=repo_dir)
    run(["git", "commit", "-q", "-m", "Add helper utility function"], cwd=repo_dir)

    return repo_dir


def test_analyze_repo_basic_counts(sample_repo):
    result = analyze_repo(str(sample_repo))
    assert result.total_commits == 3
    assert "core.py" in result.file_stats
    assert result.file_stats["core.py"].commit_count == 2
    assert "utils.py" in result.file_stats
    assert len(result.author_stats) == 1
    assert "Alice" in result.author_stats


def test_lazy_message_detection(sample_repo):
    result = analyze_repo(str(sample_repo))
    lazy = [m["message"] for m in result.lazy_messages]
    assert "wip" in lazy
    assert "Initial commit" not in lazy

def test_empty_repo(tmp_path):
    repo_dir = tmp_path / "empty"
    repo_dir.mkdir()
    run(["git", "init", "-q"], cwd=repo_dir)
    result = analyze_repo(str(repo_dir))
    assert result.total_commits == 0


def test_invalid_repo(tmp_path):
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    with pytest.raises(ValueError):
        analyze_repo(str(not_a_repo))
