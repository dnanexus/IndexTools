import contextlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Optional


@contextlib.contextmanager
def chdir(todir: Path):
    """
    Context manager that temporarily changes directories.

    Args:
        todir: The directory to change to.
    """
    curdir = Path.cwd()
    try:
        os.chdir(todir)
        yield todir
    finally:
        os.chdir(curdir)


@contextlib.contextmanager
def tempdir(
    change_dir: bool = False, tmproot: Optional[Path] = None,
    cleanup: Optional[bool] = True
) -> Path:
    """
    Context manager that creates a temporary directory, yields it, and then
    deletes it after return from the yield.

    Args:
        change_dir: Whether to temporarily change to the temp dir.
        tmproot: Root directory in which to create temporary directories.
        cleanup: Whether to delete the temporary directory before exiting the context.
    """
    temp = Path(tempfile.mkdtemp(dir=tmproot))
    try:
        if change_dir:
            with chdir(temp):
                yield temp
        else:
            yield temp
    finally:
        if cleanup:
            shutil.rmtree(temp)
