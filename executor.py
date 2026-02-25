"""
executor.py — Git clone + Docker build/run logic for DevReplicator
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from utils import log_info, log_warn, log_error, log_success


# ── Git helpers ──────────────────────────────────────────────────────────────

def check_git() -> None:
    if not shutil.which("git"):
        log_error("git is not installed or not found in PATH.")
        sys.exit(1)


def clone_repository(url: str, dest: Optional[str] = None) -> str:
    """
    Clone a GitHub repository to a local directory.
    Returns the absolute path to the cloned directory.
    """
    check_git()

    repo_name = _extract_repo_name(url)
    if dest is None:
        dest = os.path.join(tempfile.gettempdir(), f"devreplicator_{repo_name}")

    if Path(dest).exists():
        log_warn(f"Destination already exists — removing: {dest}")
        shutil.rmtree(dest)

    log_info(f"Cloning {url} → {dest}")
    result = _run(["git", "clone", "--depth=1", url, dest], stream=True)
    if result.returncode != 0:
        log_error("git clone failed. Check the URL and your network connection.")
        sys.exit(1)

    log_success(f"Repository cloned: {dest}")
    return dest


def _extract_repo_name(url: str) -> str:
    """Parse repo name from various GitHub URL formats."""
    url = url.rstrip("/").rstrip(".git")
    return url.split("/")[-1] or "repo"


# ── Docker helpers ───────────────────────────────────────────────────────────

def check_docker() -> None:
    """Verify Docker daemon is accessible, exit gracefully if not."""
    if not shutil.which("docker"):
        log_error(
            "Docker is not installed or not found in PATH.\n"
            "  Install Docker Desktop: https://docs.docker.com/get-docker/"
        )
        sys.exit(1)

    result = _run(["docker", "info"], capture=True)
    if result.returncode != 0:
        log_error(
            "Docker daemon is not running.\n"
            "  Start Docker Desktop or run: sudo systemctl start docker"
        )
        sys.exit(1)


def build_image(repo_path: str, dockerfile_path: str, image_tag: str) -> bool:
    """
    Build a Docker image from the generated Dockerfile.
    Returns True on success, False on failure.
    """
    check_docker()
    dockerfile_name = Path(dockerfile_path).name

    log_info(f"Building Docker image: {image_tag}")
    log_info(f"Context: {repo_path}  |  Dockerfile: {dockerfile_name}")

    cmd = [
        "docker", "build",
        "-f", dockerfile_path,
        "-t", image_tag,
        repo_path,
    ]

    result = _run(cmd, stream=True)
    if result.returncode != 0:
        log_error("Docker build failed. Review the output above.")
        return False

    log_success(f"Image built successfully: {image_tag}")
    return True


def run_container(
    image_tag: str,
    container_name: str,
    port_mapping: Optional[Tuple[int, int]] = None,
    detach: bool = True,
) -> bool:
    """
    Run a Docker container from the built image.
    Returns True on success, False on failure.
    """
    # Remove existing container with the same name
    _remove_existing_container(container_name)

    cmd = ["docker", "run", "--name", container_name]

    if detach:
        cmd.append("-d")

    if port_mapping:
        host_port, container_port = port_mapping
        cmd += ["-p", f"{host_port}:{container_port}"]

    cmd.append(image_tag)

    log_info(f"Starting container: {container_name}")
    result = _run(cmd, stream=not detach, capture=detach)

    if result.returncode != 0:
        log_error("Failed to start container. Review the output above.")
        return False

    if detach:
        container_id = result.stdout.strip()[:12]
        log_success(f"Container running (detached)  id={container_id}")
        _print_container_status(container_name)
        if port_mapping:
            log_info(f"Accessible at: http://localhost:{port_mapping[0]}")
    else:
        log_success("Container exited cleanly.")

    return True


def _remove_existing_container(name: str) -> None:
    result = _run(
        ["docker", "ps", "-aq", "--filter", f"name=^{name}$"],
        capture=True,
    )
    cid = result.stdout.strip()
    if cid:
        log_warn(f"Removing existing container: {name}")
        _run(["docker", "rm", "-f", cid], capture=True)


def _print_container_status(name: str) -> None:
    result = _run(
        ["docker", "ps", "--filter", f"name={name}", "--format",
         "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"],
        capture=True,
    )
    if result.stdout.strip():
        print()
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
        print()


# ── Subprocess wrapper ───────────────────────────────────────────────────────

def _run(
    cmd: list,
    stream: bool = False,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """
    Execute a subprocess command.

    stream=True  → output is printed to terminal in real time
    capture=True → output is captured and returned silently
    """
    if stream:
        proc = subprocess.run(cmd, text=True)
        return proc

    return subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
