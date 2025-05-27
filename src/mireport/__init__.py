import logging

from mireport.data import excel_templates, taxonomies
from mireport.excelprocessor import _loadVsmeDefaults
from mireport.json import loadJsonPackageResource
from mireport.taxonomy import _loadTaxonomyFromFile

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["loadMetaData"]


def loadMetaData() -> None:
    """Loads the taxonomies, unit registry and other models."""
    with loadJsonPackageResource(taxonomies, "vsme.json") as payload:
        _loadTaxonomyFromFile(payload)
    with loadJsonPackageResource(excel_templates, "vsme.json") as payload:
        _loadVsmeDefaults(payload)
