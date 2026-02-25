#!/usr/bin/env python3
"""
replicator.py — Main entry point for DevReplicator CLI
"""

import os
import re
import sys
import threading
import http.server
import webbrowser
from pathlib import Path

from utils import (
    print_banner, log_info, log_warn, log_error, log_success,
    log_step, log_section, prompt, confirm,
)
from detectors import detect_project
from docker_generator import generate_dockerfile, DOCKERFILE_NAME
from executor import clone_repository, build_image, run_container


TOTAL_STEPS = 5


def main() -> None:
    print_banner()

    # ── Mode selection ───────────────────────────────────────────
    log_section("Mode Selection")
    print(f"  [1] CLI mode   — run in this terminal")
    print(f"  [2] UI  mode   — open browser dashboard")
    print()
    mode = prompt("Choose mode (1/2) [default: 1]:") or "1"

    if mode.strip() == "2":
        _launch_ui()
        return

    _run_cli()


def _run_cli() -> None:
    log_section("DevReplicator — CLI Mode")

    # ── Input ────────────────────────────────────────────────────
    url = prompt("GitHub repository URL:")
    if not url:
        log_error("No URL provided. Exiting.")
        sys.exit(1)

    if not _valid_github_url(url):
        log_warn("URL does not look like a GitHub repository. Proceeding anyway …")

    # ── Step 1: Clone ────────────────────────────────────────────
    log_section("Step 1 / 5 — Cloning Repository")
    log_step(1, TOTAL_STEPS, f"Cloning: {url}")
    repo_path = clone_repository(url)

    # ── Step 2: Detect ───────────────────────────────────────────
    log_section("Step 2 / 5 — Detecting Project Type")
    log_step(2, TOTAL_STEPS, "Analyzing project structure …")
    info = detect_project(repo_path)

    log_info(f"Project type   : {info.project_type}")
    log_info(f"Dependency file: {info.dep_file or 'None'}")
    log_info(f"Entry point    : {info.entry_point or 'None'}")
    log_info(f"Base image     : {info.base_image or 'Not determined'}")

    # ── Handle unknown project ───────────────────────────────────
    if info.project_type == "unknown":
        log_warn("Project type could not be determined automatically.")
        info.base_image    = prompt("Enter Docker base image (e.g. ubuntu:22.04):") or "ubuntu:22.04"
        info.start_command = prompt("Enter start command (e.g. bash):") or "bash"

    # ── Handle missing entry point ───────────────────────────────
    if not info.entry_point and info.project_type in ("python", "poetry"):
        custom_entry = prompt("Entry point not found. Specify filename (or press Enter to skip):").strip()
        if custom_entry:
            info.entry_point    = custom_entry
            info.start_command  = f"python {custom_entry}"

    # ── Step 3: Generate Dockerfile ──────────────────────────────
    log_section("Step 3 / 5 — Generating Dockerfile")
    log_step(3, TOTAL_STEPS, "Generating Dockerfile …")
    dockerfile_path = generate_dockerfile(repo_path, info)

    # ── Step 4: Build image ──────────────────────────────────────
    image_tag      = _slugify(url)
    container_name = f"devreplicator-{image_tag}"

    log_section("Step 4 / 5 — Building Docker Image")
    log_step(4, TOTAL_STEPS, f"Building image: {image_tag}")

    success = build_image(repo_path, dockerfile_path, image_tag)
    if not success:
        log_error("Build failed. Aborting.")
        sys.exit(1)

    # ── Step 5: Run container ────────────────────────────────────
    log_section("Step 5 / 5 — Running Container")
    log_step(5, TOTAL_STEPS, "Starting container …")

    port_mapping = None
    if info.project_type == "node":
        host_port = int(prompt("Map host port (default 3000):") or "3000")
        port_mapping = (host_port, 3000)
    elif info.project_type in ("python", "poetry"):
        use_port = confirm("Expose a port? (e.g. for Flask/FastAPI)", default=False)
        if use_port:
            host_port      = int(prompt("Host port (default 8000):") or "8000")
            container_port = int(prompt("Container port (default 8000):") or "8000")
            port_mapping   = (host_port, container_port)

    detach = confirm("Run container in background (detached)?", default=True)
    run_container(image_tag, container_name, port_mapping=port_mapping, detach=detach)

    # ── Done ─────────────────────────────────────────────────────
    log_section("Complete")
    log_success("DevReplicator finished successfully.")
    log_info(f"Image:     {image_tag}")
    log_info(f"Container: {container_name}")
    log_info(f"Source:    {repo_path}")
    print()
    log_info("Useful commands:")
    print(f"  docker logs -f {container_name}")
    print(f"  docker exec -it {container_name} bash")
    print(f"  docker stop {container_name}")
    print(f"  docker rm   {container_name}")
    print()


def _launch_ui() -> None:
    """Serve the UI directory and open it in the default browser."""
    ui_dir = Path(__file__).parent / "ui"
    if not ui_dir.exists():
        log_error("UI directory not found.")
        sys.exit(1)

    port = 7474
    os.chdir(ui_dir)

    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass  # suppress request logs

    server = http.server.HTTPServer(("127.0.0.1", port), _QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{port}/index.html"
    log_success(f"UI running at {url}")
    log_info("Press Ctrl+C to stop.")
    webbrowser.open(url)

    try:
        thread.join()
    except KeyboardInterrupt:
        log_info("Shutting down UI server.")
        server.shutdown()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _valid_github_url(url: str) -> bool:
    return bool(re.match(r"https?://(www\.)?github\.com/.+/.+", url))


def _slugify(url: str) -> str:
    """Convert a GitHub URL to a Docker-safe image tag."""
    name = url.rstrip("/").rstrip(".git").split("github.com/")[-1]
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", name).lower().strip("-")
    return f"devreplicator-{name}"[:128]


if __name__ == "__main__":
    main()
