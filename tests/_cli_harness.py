from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
import os
import sys

from _local_package import load_local_package

load_local_package()
from omh.cli import main


@contextmanager
def _redirect_stdin(stream):
    previous = sys.stdin
    sys.stdin = stream
    try:
        yield
    finally:
        sys.stdin = previous


def run_cli(args: list[str], *, output_json: bool = True, stdin_text: str = "") -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    stdin = StringIO(stdin_text)
    previous_output = os.environ.get("OMH_OUTPUT")
    if output_json:
        os.environ["OMH_OUTPUT"] = "json"
    else:
        os.environ.pop("OMH_OUTPUT", None)
    with _redirect_stdin(stdin), redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            status = main(args)
        finally:
            if previous_output is None:
                os.environ.pop("OMH_OUTPUT", None)
            else:
                os.environ["OMH_OUTPUT"] = previous_output
    return status, stdout.getvalue(), stderr.getvalue()
