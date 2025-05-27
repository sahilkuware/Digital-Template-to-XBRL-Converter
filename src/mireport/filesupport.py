import re
from io import BytesIO
from typing import NamedTuple

ZIP_UNWANTED_RE = re.compile(r"[^\w.]+")  # \w includes '_'
FILE_UNWANTED_RE = re.compile(r'[<>:"/\\|?*]')


def is_valid_filename(filename: str) -> bool:
    """Checks if the filename is valid for Windows."""
    # Disallowed names (case-insensitive)
    reserved_names = {
        "CON",
        "AUX",
        "NUL",
        "PRN",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    # Ensure filename is not "." or ".."
    if filename in {".", ".."}:
        return False

    # Ensure filename does not match a reserved name (case-insensitive)
    if filename.upper() in reserved_names:
        return False

    # Ensure filename does not contain invalid characters
    if FILE_UNWANTED_RE.search(filename):
        return False

    return True


def zipSafeString(original: str, fallback: str = "fallback") -> str:
    # Use no-args version of split to replace one or more whitespace chars with
    # underscore
    new = "_".join(original.split())
    new = ZIP_UNWANTED_RE.sub("_", new)
    if not (new and is_valid_filename(new)):
        new = fallback
    return new


class FilelikeAndFileName(NamedTuple):
    fileContent: bytes
    filename: str

    def fileLike(self) -> BytesIO:
        return BytesIO(self.fileContent)
