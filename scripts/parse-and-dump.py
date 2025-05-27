#!/usr/bin/env python
import sys
import time
from contextlib import closing
from pathlib import Path

from mireport.excelutil import (
    checkExcelFilePath,
    getNamedRanges,
    loadExcelFromPathOrFileLike,
)

MAXIMUM_INTERESTING_ROWS = 10


def main() -> None:
    if 2 > len(sys.argv):
        raise SystemExit("give me a file please")

    start = time.perf_counter_ns()
    excel_file = Path(sys.argv[1])
    checkExcelFilePath(excel_file)
    with closing(loadExcelFromPathOrFileLike(excel_file)) as wb:
        print(f"Opened {excel_file}")
        print("Found sheets:", *wb.sheetnames, sep="\n\t")
        print(f"Found {len(wb.defined_names)} named ranges to query for data.")
        start = time.perf_counter_ns()
        facts = getNamedRanges(wb)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000

    print(
        f"Queried all named ranges and found {len(facts)} non-empty ranges in {elapsed:,.2f} ms."
    )
    # input("Press enter to dump range names and values")
    for name, cells in sorted(facts.items()):
        num = len(cells)
        print(f"{name}: ({num} cells in range)")
        print("\t", end="")

        if all([x is None for x in cells]):
            print("(all cells empty)")
            continue

        if (total := len(cells)) > MAXIMUM_INTERESTING_ROWS:
            size = int(MAXIMUM_INTERESTING_ROWS / 2)
            cells = (
                cells[:size]
                + [f"... supressed {total - MAXIMUM_INTERESTING_ROWS} rows..."]
                + cells[-size:]
            )
        print(*cells, sep="\n\t")
    elapsed = (time.perf_counter_ns() - start) / 1_000_000_000
    print(f"Finished dumping Excel named ranges ({elapsed:,.2f} seconds elapsed).")


if __name__ == "__main__":
    main()
