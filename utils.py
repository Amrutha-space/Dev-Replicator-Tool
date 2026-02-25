"""
utils.py — Shared helpers for DevReplicator
"""

import sys
from datetime import datetime


RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
GREEN   = "\033[38;5;82m"
CYAN    = "\033[38;5;51m"
YELLOW  = "\033[38;5;220m"
RED     = "\033[38;5;196m"
BLUE    = "\033[38;5;33m"
MAGENTA = "\033[38;5;171m"
GRAY    = "\033[38;5;245m"


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log_info(msg: str) -> None:
    print(f"{GRAY}[{_timestamp()}]{RESET} {CYAN}›{RESET} {msg}")


def log_success(msg: str) -> None:
    print(f"{GRAY}[{_timestamp()}]{RESET} {GREEN}✔{RESET} {BOLD}{msg}{RESET}")


def log_warn(msg: str) -> None:
    print(f"{GRAY}[{_timestamp()}]{RESET} {YELLOW}⚠{RESET}  {YELLOW}{msg}{RESET}")


def log_error(msg: str) -> None:
    print(f"{GRAY}[{_timestamp()}]{RESET} {RED}✖{RESET} {RED}{BOLD}{msg}{RESET}", file=sys.stderr)


def log_step(step: int, total: int, msg: str) -> None:
    bar = f"{BLUE}[{step}/{total}]{RESET}"
    print(f"{GRAY}[{_timestamp()}]{RESET} {bar} {MAGENTA}→{RESET} {msg}")


def log_section(title: str) -> None:
    width = 60
    print()
    print(f"{DIM}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{DIM}{'─' * width}{RESET}")


def print_banner() -> None:
    banner = f"""
{CYAN}{BOLD}
  ██████╗ ███████╗██╗   ██╗██████╗ ███████╗██████╗ 
  ██╔══██╗██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗
  ██║  ██║█████╗  ██║   ██║██████╔╝█████╗  ██████╔╝
  ██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██╔══╝  ██╔═══╝ 
  ██████╔╝███████╗ ╚████╔╝ ██║  ██║███████╗██║      
  ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚═╝      
{RESET}{GRAY}  Replicator — Instant Docker Dev Environments
  v1.0.0 · Python {sys.version.split()[0]}{RESET}
"""
    print(banner)


def prompt(msg: str) -> str:
    return input(f"{CYAN}?{RESET} {BOLD}{msg}{RESET} ").strip()


def confirm(msg: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    answer = input(f"{CYAN}?{RESET} {BOLD}{msg} {GRAY}{hint}{RESET} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")
