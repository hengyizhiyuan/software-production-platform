"""Filesystem cleanup for disposable Git checkouts across host platforms."""

import os
from pathlib import Path
import shutil
import stat
import time


def _retry_readonly_file_removal(function, path, error: BaseException) -> None:
    if not isinstance(error, PermissionError):
        raise error
    mode = os.lstat(path).st_mode
    if not stat.S_ISREG(mode) or mode & stat.S_IWRITE:
        raise error
    os.chmod(path, mode | stat.S_IWRITE)
    function(path)


def remove_git_tree(path: Path) -> None:
    """Remove a checkout while preserving unrelated filesystem failures."""
    for attempt in range(8):
        try:
            shutil.rmtree(path, onexc=_retry_readonly_file_removal)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) != 32 or attempt == 7:
                raise
            time.sleep(0.25 * (attempt + 1))


def replace_git_tree(source: Path, destination: Path) -> None:
    """Wait briefly for Windows to release a completed Git checkout."""
    for attempt in range(8):
        try:
            source.replace(destination)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) != 32 or attempt == 7:
                raise
            time.sleep(0.25 * (attempt + 1))
