"""
detectors.py — Project type detection logic for DevReplicator
"""

import os
import re
from pathlib import Path
from typing import Optional
from utils import log_info, log_warn


PYTHON_ENTRY_CANDIDATES = ["app.py", "main.py", "server.py", "run.py", "manage.py", "cli.py"]
NODE_ENTRY_CANDIDATES   = ["index.js", "server.js", "app.js", "main.js", "src/index.js"]


class ProjectInfo:
    def __init__(
        self,
        project_type: str,
        entry_point: Optional[str],
        dep_file: Optional[str],
        base_image: Optional[str],
        start_command: Optional[str],
        scanned_imports: Optional[list] = None,
    ):
        self.project_type   = project_type          # "python", "poetry", "node", "unknown"
        self.entry_point    = entry_point
        self.dep_file       = dep_file
        self.base_image     = base_image
        self.start_command  = start_command
        self.scanned_imports = scanned_imports or []

    def __repr__(self) -> str:
        return (
            f"ProjectInfo(type={self.project_type!r}, entry={self.entry_point!r}, "
            f"dep_file={self.dep_file!r})"
        )


def detect_project(repo_path: str) -> ProjectInfo:
    """
    Examine a cloned repository directory and return a ProjectInfo
    describing the detected technology stack.
    """
    root = Path(repo_path)

    # ── Python / pip ────────────────────────────────────────────
    if (root / "requirements.txt").exists():
        log_info("Detected: requirements.txt → Python (pip) project")
        entry = _find_python_entry(root)
        return ProjectInfo(
            project_type="python",
            entry_point=entry,
            dep_file="requirements.txt",
            base_image="python:3.11-slim",
            start_command=f"python {entry}" if entry else None,
        )

    # ── Python / Poetry ─────────────────────────────────────────
    if (root / "pyproject.toml").exists():
        log_info("Detected: pyproject.toml → Python (Poetry) project")
        entry = _find_python_entry(root)
        return ProjectInfo(
            project_type="poetry",
            entry_point=entry,
            dep_file="pyproject.toml",
            base_image="python:3.11-slim",
            start_command=f"python {entry}" if entry else None,
        )

    # ── Node.js ─────────────────────────────────────────────────
    if (root / "package.json").exists():
        log_info("Detected: package.json → Node.js project")
        entry = _find_node_entry(root)
        return ProjectInfo(
            project_type="node",
            entry_point=entry,
            dep_file="package.json",
            base_image="node:18-slim",
            start_command="npm start",
        )

    # ── Fallback: scan Python imports ────────────────────────────
    py_files = list(root.rglob("*.py"))
    if py_files:
        log_warn("No dependency file found. Scanning Python imports …")
        imports = _scan_python_imports(py_files)
        entry   = _find_python_entry(root)
        if imports:
            log_info(f"Discovered imports: {', '.join(sorted(imports)[:10])}")
        return ProjectInfo(
            project_type="python",
            entry_point=entry,
            dep_file=None,
            base_image="python:3.11-slim",
            start_command=f"python {entry}" if entry else None,
            scanned_imports=list(imports),
        )

    # ── Unknown ──────────────────────────────────────────────────
    log_warn("Could not determine project type automatically.")
    return ProjectInfo(
        project_type="unknown",
        entry_point=None,
        dep_file=None,
        base_image=None,
        start_command=None,
    )


def _find_python_entry(root: Path) -> Optional[str]:
    for candidate in PYTHON_ENTRY_CANDIDATES:
        if (root / candidate).exists():
            log_info(f"Entry point detected: {candidate}")
            return candidate
    log_warn("No standard Python entry point found (app.py / main.py / server.py).")
    return None


def _find_node_entry(root: Path) -> Optional[str]:
    # Check package.json "main" field first
    pkg = root / "package.json"
    if pkg.exists():
        import json
        try:
            data = json.loads(pkg.read_text())
            main = data.get("main")
            if main and (root / main).exists():
                log_info(f"Entry point from package.json[main]: {main}")
                return main
        except (json.JSONDecodeError, KeyError):
            pass

    for candidate in NODE_ENTRY_CANDIDATES:
        if (root / candidate).exists():
            log_info(f"Entry point detected: {candidate}")
            return candidate

    log_warn("No standard Node.js entry point found.")
    return None


def _scan_python_imports(py_files: list) -> set:
    """
    Perform a best-effort scan of third-party imports from .py files.
    Returns a set of probable package names (excludes stdlib & relative).
    """
    stdlib_prefixes = {
        "os", "sys", "re", "io", "abc", "ast", "csv", "json", "math",
        "time", "enum", "uuid", "copy", "glob", "gzip", "hmac", "html",
        "http", "logging", "pathlib", "shutil", "socket", "struct",
        "string", "threading", "traceback", "typing", "unittest",
        "urllib", "xml", "zipfile", "subprocess", "collections",
        "contextlib", "dataclasses", "datetime", "functools", "hashlib",
        "inspect", "itertools", "multiprocessing", "operator", "random",
        "signal", "stat", "tempfile", "textwrap", "warnings",
    }

    import_re = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)")
    found = set()

    for fpath in py_files:
        try:
            for line in fpath.read_text(errors="ignore").splitlines():
                m = import_re.match(line)
                if m:
                    pkg = m.group(1)
                    if pkg not in stdlib_prefixes:
                        found.add(pkg)
        except OSError:
            continue

    return found
