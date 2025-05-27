from contextlib import contextmanager
from importlib.resources import Package, files
from json import load
from typing import Generator

__all__ = ["loadJsonPackageResource"]


@contextmanager
def loadJsonPackageResource(module: Package, filename: str) -> Generator:
    source = files(module).joinpath(filename)
    with source.open("rb") as jf:
        yield load(jf)
