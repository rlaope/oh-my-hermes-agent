from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from _local_package import load_local_package

load_local_package()
from omh.cli import main


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()
