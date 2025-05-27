import os
from argparse import ArgumentParser
from glob import glob


def getListofPathsFromListOfGlobs(globs: list[str]) -> list[str]:
    paths = [
        glob_result for glob_candidate in globs for glob_result in glob(glob_candidate)
    ]
    return paths


def validateTaxonomyPackages(globList: list[str], parser: ArgumentParser) -> list[str]:
    print("Zip files specified", " ".join(globList))
    taxonomy_zips: list[str] = getListofPathsFromListOfGlobs(globList)
    print("Zip files to use  ", " ".join(taxonomy_zips))

    if not all([os.path.exists(taxonomy_zip) for taxonomy_zip in taxonomy_zips]):
        raise parser.error(f"Not all specified files found: {taxonomy_zips}")
    elif not all([taxonomy_zip.endswith(".zip") for taxonomy_zip in taxonomy_zips]):
        raise parser.error(f"Not all specified files are Zip files: {taxonomy_zips}")
    return taxonomy_zips
