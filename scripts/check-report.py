import argparse
import glob
import shutil
import time
from pathlib import Path

from mireport.arelle.report_info import ArelleReportProcessor, getOrCreateReportPackage


def parse_args() -> argparse.Namespace:
    argparser = argparse.ArgumentParser(
        description="Check a report package is valid and create a viewer for it including any validation messages."
    )
    argparser.add_argument(
        "report_path",
        type=Path,
        help="Path to the report package to be checked.",
    )
    argparser.add_argument(
        "--taxonomy_packages",
        type=str,
        nargs="+",
        default=[],
        help="Paths to the taxonomy packages to be used (globs, *.zip, are permitted).",
    )
    argparser.add_argument(
        "--viewer-path",
        type=Path,
        default=None,
        help="The path of the viewer to be created.",
    )
    args = argparser.parse_args()
    return args


def main() -> None:
    start = time.perf_counter_ns()

    args = parse_args()
    report_path: Path = args.report_path
    taxonomy_package_globs: list[str] = args.taxonomy_packages
    viewer_path: Path = args.viewer_path

    taxonomy_packages: list[Path] = []
    if taxonomy_package_globs:
        workOffline = True
        print("Zip files specified", " ".join(taxonomy_package_globs))
        taxonomy_packages.extend(
            sorted(
                [
                    Path(glob_result)
                    for glob_candidate in taxonomy_package_globs
                    for glob_result in glob.glob(glob_candidate)
                ],
                key=lambda x: x.name,
            )
        )
        print("Zip files to use  ", " ".join(str(t) for t in taxonomy_packages))

        if not all([taxonomy_zip.is_file() for taxonomy_zip in taxonomy_packages]):
            raise SystemExit(f"Not all specified files found: {taxonomy_packages}")
        elif not all(
            [".zip" == taxonomy_zip.suffix for taxonomy_zip in taxonomy_packages]
        ):
            raise SystemExit(
                f"Not all specified files are Zip files: {taxonomy_packages}"
            )

    if taxonomy_packages:
        workOffline = True
        print("Taxonomy packages specified so working OFFLINE.")
    else:
        print("No taxonomy packages specified so working ONLINE.")
        workOffline = False

    if not report_path.is_file():
        raise SystemExit(f"Report path {report_path} cannot be found.")

    start = time.perf_counter_ns()
    print("Calling into Arelle")
    a = ArelleReportProcessor(
        taxonomyPackages=taxonomy_packages, workOffline=workOffline
    )
    source = getOrCreateReportPackage(report_path)

    if not viewer_path:
        result = a.validateReportPackage(source)
    else:
        if viewer_path.is_file():
            print(f"Overwriting {viewer_path}.")
        result = a.generateInlineViewer(source)
        with open(viewer_path, "wb") as out:
            shutil.copyfileobj(result.viewer.fileLike(), out)
    if result.logLines:
        print("\t", end="")
        print(*result.logLines, sep="\n\t")
    elapsed = (time.perf_counter_ns() - start) / 1_000_000_000
    print(f"Finished querying Arelle ({elapsed:,.2f} seconds elapsed).")


if __name__ == "__main__":
    main()
