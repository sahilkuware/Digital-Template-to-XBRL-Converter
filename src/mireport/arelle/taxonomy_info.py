import json
import logging
import time
from collections import defaultdict
from typing import Any, Optional

from arelle import XbrlConst
from arelle.api.Session import Session
from arelle.Cntlr import Cntlr
from arelle.logging.handlers.LogToXmlHandler import LogToXmlHandler
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelRelationshipSet import ModelRelationshipSet
from arelle.ModelValue import QName
from arelle.ModelXbrl import ModelXbrl
from arelle.RuntimeOptions import RuntimeOptions
from arelle.utils.PluginData import PluginData
from arelle.ValidateUtr import UtrEntry

from mireport.arelle.support import (
    ArelleObjectJSONEncoder,
    ArelleProcessingResult,
    ArelleRelatedException,
)
from mireport.taxonomy import MEASUREMENT_GUIDANCE_LABEL_ROLE

PLUGIN_NAME = "Taxonomy Information Extractor"


def callArelleForTaxonomyInfo(
    entry_point: str,
    taxonomy_zips: list[str],
    taxonomy_json_path: str,
    utr_json_path: Optional[str] = None,
) -> ArelleProcessingResult:
    pluginOptions = {"taxonomyDataFile": taxonomy_json_path}
    utrValidation = False
    if utr_json_path is not None:
        pluginOptions["utrDataFile"] = utr_json_path
        utrValidation = True

    options = RuntimeOptions(
        abortOnMajorError=True,
        entrypointFile=entry_point,
        internetConnectivity="offline",
        keepOpen=False,
        logFormat="%(asctime)s [%(messageCode)s] %(message)s - %(file)s",
        logPropagate=False,
        packages=taxonomy_zips,
        pluginOptions=pluginOptions,
        plugins=__file__,
        validate=True,
        utrValidate=utrValidation,
    )
    with Session() as session:
        log_handler = LogToXmlHandler()
        session.run(
            options,
            logHandler=log_handler,
            logFilters=[],
        )
        results = ArelleProcessingResult.fromLogToXmlHandler(log_handler)
    return results


class TaxonomyInfoPluginData(PluginData):
    Taxonomy: dict = dict()
    UTR: dict = dict()


def pluginData(cntlr: Cntlr) -> TaxonomyInfoPluginData:
    pluginData = cntlr.getPluginData(PLUGIN_NAME)
    if pluginData is None:
        pluginData = TaxonomyInfoPluginData(PLUGIN_NAME)
        cntlr.setPluginData(pluginData)
    return pluginData


def writeDataFile(
    cntlr: Cntlr,
    jsonPath: str,
    dataType: str,
) -> None:
    pdata = pluginData(cntlr)
    data = getattr(pdata, dataType, None)
    if not data:
        cntlr.addToLog(f"No {dataType} data to write")
        return

    with open(jsonPath, "w", encoding="UTF-8") as f:
        tidied = ArelleObjectJSONEncoder.tidyKeys(data)
        json.dump(tidied, f, indent=2, sort_keys=True, cls=ArelleObjectJSONEncoder)
        cntlr.addToLog(f"{dataType} data written to {jsonPath}")


class UTRInfoExtractor:
    def __init__(
        self, cntlr: Cntlr, modelXbrl: ModelXbrl, pData: TaxonomyInfoPluginData
    ):
        self.cntlr: Cntlr = cntlr
        self.modelXbrl: ModelXbrl = modelXbrl
        self.pluginData: TaxonomyInfoPluginData = pData
        if (
            utrModel := getattr(
                self.modelXbrl.modelManager.disclosureSystem, "utrItemTypeEntries", None
            )
        ) is not None:
            self.utrModel: dict[str, dict[str, UtrEntry]] = utrModel
        else:
            message = (
                "No UTR entries found. Perhaps you forgot to set `utrValidate=True`?"
            )
            self.cntlr.addToLog(message)
            raise ArelleRelatedException(message)

    def extract(self) -> None:
        self.pluginData.UTR.update(
            {
                "utr": self.getUTRForJSON(),
            }
        )

    def getUTRForJSON(self) -> list[dict]:
        """Get the UTR entries from the modelXbrl."""
        # N.B. UTR schema primary key is the status and unitId
        jUTR: list[dict] = []
        interestingKeys = [
            "unitId",
            "unitName",
            "nsUnit",
            "itemType",
            "nsItemType",
            "numeratorItemType",
            "nsNumeratorItemType",
            "definition",
            "denominatorItemType",
            "nsDenominatorItemType",
            "symbol",
            "status",
        ]
        utrEntries = [
            u
            for dataTypeIsh in self.utrModel.keys()
            for u in self.utrModel[dataTypeIsh].values()
        ]
        for entry in sorted(utrEntries, key=lambda e: e.unitId):
            jEntry = {}
            for key in interestingKeys:
                if (value := getattr(entry, key)) is not None and value.strip() != "":
                    jEntry[key] = value
            jUTR.append(jEntry)
        return jUTR


class TaxonomyInfoExtractor:
    def __init__(self, cntlr: Cntlr, options: RuntimeOptions, modelXbrl: ModelXbrl):
        self.cntlr: Cntlr = cntlr
        self.options: RuntimeOptions = options
        self.modelXbrl: ModelXbrl = modelXbrl
        self.taxonomyJson: dict[str, dict] = defaultdict(dict)

    def extract(self) -> None:
        self.taxonomyJson["entryPoint"] = self.options.entrypointFile

        self.extractPresentation()
        self.extractDimensionDefinitions()
        self.extractConceptsAndMetadata()

        self.cntlr.addToLog("Processing namespaces and namespace prefixes")
        self.taxonomyJson["namespaces"] = self.modelXbrl.prefixedNamespaces
        pdata = pluginData(self.cntlr)
        pdata.Taxonomy.update(self.taxonomyJson)

        if self.options.utrValidate:
            self.cntlr.addToLog(
                "UTR validation is on so attempting to process UTR entries"
            )
            utrExtractor = UTRInfoExtractor(self.cntlr, self.modelXbrl, pdata)
            utrExtractor.extract()

    def walkChildren(
        self,
        parent_concept: ModelConcept,
        elrUri: str,
        relSet: ModelRelationshipSet,
        rows: list[tuple[int, QName, bool | str | None]],
        indent: int,
        includeUsable: bool = False,
    ) -> None:
        for rel in relSet.fromModelObject(parent_concept):
            child_concept = rel.toModelObject
            if includeUsable:
                rows.append((indent, child_concept.qname, rel.isUsable))
            else:
                rows.append((indent, child_concept.qname, None))
            self.walkChildren(
                child_concept, elrUri, relSet, rows, indent + 1, includeUsable
            )

    def getPrimaryItems(
        self, elrUri: str, root_concept: ModelConcept
    ) -> list[tuple[int, QName]]:
        # Placeholder implementation for getPrimaryItems
        # Replace this with the actual logic to retrieve primary items
        relSet = self.modelXbrl.relationshipSet(XbrlConst.domainMember, elrUri)
        rows: list[tuple[int, QName, bool | str | None]] = []
        rows.append((0, root_concept.qname, None))
        assert root_concept in relSet.rootConcepts, (
            f"{root_concept} should be in {relSet.rootConcepts}"
        )
        self.walkChildren(root_concept, elrUri, relSet, rows, 1)
        return [(i, qname) for i, qname, _ in rows]

    def getDimensions(self, elrUri: str, hypercube: ModelConcept) -> list[ModelConcept]:
        # Placeholder implementation for getDimensions
        # Replace this with the actual logic to retrieve dimensions
        relSet = self.modelXbrl.relationshipSet(XbrlConst.hypercubeDimension, elrUri)
        roots = relSet.rootConcepts
        assert hypercube in roots, f"{hypercube} should be in {relSet.rootConcepts}"
        assert len(roots) == 1, (
            f"{elrUri} has more than one hypercube [{relSet.rootConcepts}]. Exciting!"
        )
        return [rel.toModelObject for rel in relSet.fromModelObject(hypercube)]

    def getDomainMembersForExplicitDimension(
        self, elrUri: str, explicitDimension: ModelConcept
    ) -> list[tuple[int, QName]]:
        # Placeholder implementation for getDimensions
        # Replace this with the actual logic to retrieve dimensions
        dimensionDomainRelSet = self.modelXbrl.relationshipSet(
            XbrlConst.dimensionDomain, elrUri
        )
        assert explicitDimension in dimensionDomainRelSet.rootConcepts, (
            f"{explicitDimension} should be in {dimensionDomainRelSet.rootConcepts}"
        )
        domainConcepts = [
            (rel.toModelObject, rel.isUsable)
            for rel in dimensionDomainRelSet.fromModelObject(explicitDimension)
        ]
        domainMemberRelSet = self.modelXbrl.relationshipSet(
            XbrlConst.domainMember, elrUri
        )
        assert all(
            domainConcept in domainMemberRelSet.rootConcepts
            for domainConcept, _ in domainConcepts
        ), f"{domainConcepts} should all be in {domainMemberRelSet.rootConcepts}"
        rows = []
        for domainConcept, usable in domainConcepts:
            rows.append((0, domainConcept.qname, usable))
            self.walkChildren(
                domainConcept, elrUri, domainMemberRelSet, rows, 1, includeUsable=True
            )
        qnames = sorted({q for _, q, usable in rows if usable})
        return qnames

    def getDomainMembersForEE(
        self, elrUri: str, headUsable: bool, domainConcept: ModelConcept
    ) -> list[QName]:
        """Deliberately over simplified for now."""
        domainMemberRelSet = self.modelXbrl.relationshipSet(
            XbrlConst.domainMember, elrUri
        )
        rows: list[tuple[int, QName, bool | str | None]] = []
        self.walkChildren(
            domainConcept, elrUri, domainMemberRelSet, rows, 1, includeUsable=True
        )
        if headUsable:
            rows.insert(0, (0, domainConcept.qname, headUsable))
        result: list[QName] = [q for _, q, usable in rows if usable]
        return result

    def getDimensionDefaults(self) -> dict[QName, QName]:
        defaults: dict[QName, QName] = {}
        elrsWithDefaults = set()
        for arcroleUri, elrUri, linkqname, arcqname in self.modelXbrl.baseSets.keys():
            if arcroleUri == XbrlConst.dimensionDefault and elrUri is not None:
                elrsWithDefaults.add(elrUri)
        for elrUri in elrsWithDefaults:
            dimensionDefaultRelSet = self.modelXbrl.relationshipSet(
                XbrlConst.dimensionDefault, elrUri
            )
            dimensions: list[ModelConcept] = dimensionDefaultRelSet.rootConcepts
            for d in dimensions:
                members: list[ModelConcept] = [
                    rel.toModelObject
                    for rel in dimensionDefaultRelSet.fromModelObject(d)
                ]
                assert len(members) == 1, (
                    f"More than one default for dimension {d} in {elrUri}, {members}."
                )
                assert d not in defaults, (
                    f"Default defined more than once for {d}. Last seen in {elrUri}."
                )
                defaults[d.qname] = members[0].qname
        return defaults

    def addConceptMetadata(self, concept: ModelConcept, jconcept: dict) -> None:
        meta = {
            "abstract": "isAbstract",
            "dimension": "isDimensionItem",
            "hypercube": "isHypercubeItem",
            "nillable": "isNillable",
            "numeric": "isNumeric",
        }
        for json_key, concept_property in meta.items():
            if (value := getattr(concept, concept_property)) is True:
                jconcept[json_key] = value

    def extractConceptsAndMetadata(self) -> None:
        self.cntlr.addToLog("Processing concepts (including labels and references)")
        for qname, concept in sorted(self.modelXbrl.qnameConcepts.items()):
            if concept.isItem:
                if concept.qname.namespaceURI in (XbrlConst.xbrli, XbrlConst.xbrldt):
                    # We don't need/want xbrli:item, xbrldt:dimensionItem or
                    # xbrldt:hypercubeItem in our concept list. Arelle docs
                    # suggests isItem should supress xbrli:item but it doesn't.
                    continue
                jconcept = {
                    # We use concept.type.qname as it gets the namespace prefix
                    # right, i.e. something defined in modelXbrl.prefixedNamespace.
                    # concept.typeQname works almost the same but prefers to use a
                    # prefix from ?the defining schema? and can use one that is not
                    # defined in modelXbrl.prefixedNamespace which makes it
                    # impossible to find the namespace
                    "dataType": concept.type.qname,
                    "baseDataType": concept.baseXbrliTypeQname,
                    "periodType": concept.periodType,
                    "labels": {
                        "en": {
                            XbrlConst.standardLabel: concept.label(
                                fallbackToQname=False,
                                preferredLabel=XbrlConst.standardLabel,
                                lang="en",
                                strip=True,
                            ),
                        }
                    },
                }
                self.addConceptMetadata(concept, jconcept)

                if (
                    measurement := concept.label(
                        fallbackToQname=False,
                        preferredLabel=MEASUREMENT_GUIDANCE_LABEL_ROLE,
                        lang="en",
                        strip=True,
                    )
                ) is not None:
                    jconcept["labels"]["en"][MEASUREMENT_GUIDANCE_LABEL_ROLE] = (
                        measurement
                    )

                if (
                    documentation := concept.label(
                        fallbackToQname=False,
                        preferredLabel=XbrlConst.documentationLabel,
                        lang="en",
                        strip=True,
                    )
                ) is not None:
                    jconcept["labels"]["en"][XbrlConst.documentationLabel] = (
                        documentation
                    )

                if concept.isEnumeration and not concept.isEnumeration2Item:
                    self.cntlr.addToLog(
                        f"Warning extensible enumerations other than 2.0 are not supported. {concept.qname}",
                        level=logging.WARN,
                    )
                if concept.isEnumeration2Item:
                    # is this even needed? We can lookup the labels, get the concept
                    # names and bung them in without using this. If this had a list
                    # of the valid qnames for the domain, this would act as a check
                    # that the chosen name is valid for the domain.
                    headUsable = concept.isEnumDomainUsable
                    linkrole = concept.enumLinkrole
                    jconcept.setdefault("other", {})["ee20DomainMembers"] = (
                        self.getDomainMembersForEE(
                            linkrole,
                            headUsable,
                            self.modelXbrl.qnameConcepts[concept.enumDomainQname],
                        )
                    )
                if concept.isTypedDimension:
                    jconcept.setdefault("other", {})["typedElement"] = (
                        concept.typedDomainElement.qname
                    )
                self.taxonomyJson["concepts"][qname] = jconcept

    def extractDimensionDefinitions(self) -> None:
        self.cntlr.addToLog("Processing dimensions")
        self.taxonomyJson["dimensions"] = defaultdict(dict)
        # Get the hypercubes and primary items
        hypercubeArcRoles = (XbrlConst.all, XbrlConst.notAll)
        for arcroleUri, elrUri, linkqname, arcqname in self.modelXbrl.baseSets.keys():
            if linkqname is None or arcqname is None:
                continue
            if arcroleUri.startswith(XbrlConst.dimStartsWith):
                # TODO: detect and raise an error if there are any targetRole switches
                # as we don't handle them yet (or, alternately, handle them!)
                pass
            if arcroleUri in hypercubeArcRoles and elrUri is not None:
                relSet = self.modelXbrl.relationshipSet(hypercubeArcRoles, elrUri)
                for root_concept in relSet.rootConcepts:
                    for rel in relSet.fromModelObject(root_concept):
                        concept: ModelConcept = rel.toModelObject
                        if concept.isHypercubeItem:
                            cube = {
                                "primaryItems": self.getPrimaryItems(
                                    elrUri, root_concept
                                ),
                                "xbrldt:contextElement": rel.contextElement,
                                "xbrldt:closed": rel.isClosed,
                            }
                            for dimension in self.getDimensions(elrUri, concept):
                                if dimension.isExplicitDimension:
                                    cube.setdefault("explicitDimensions", {})[
                                        dimension.qname
                                    ] = self.getDomainMembersForExplicitDimension(
                                        elrUri, dimension
                                    )
                                elif dimension.isTypedDimension:
                                    cube.setdefault("typedDimensions", []).append(
                                        dimension.qname
                                    )
                            self.taxonomyJson["dimensions"][elrUri][concept.qname] = (
                                cube
                            )
                        else:
                            raise ArelleRelatedException(
                                f"Found a {concept} but expected a hypercube."
                            )

        self.cntlr.addToLog("Processing dimension defaults")
        self.taxonomyJson["dimensions"]["_defaults"] = self.getDimensionDefaults()

    def extractPresentation(self) -> None:
        self.cntlr.addToLog("Processing presentation network")
        for arcroleUri, elrUri, linkqname, arcqname in self.modelXbrl.baseSets.keys():
            # cntlr.addToLog(f"{arcroleUri}, {elrUri}, {linkqname}, {arcqname}")
            if linkqname is None or arcqname is None:
                continue
            if arcroleUri == XbrlConst.parentChild and elrUri is not None:
                self.cntlr.addToLog(f"Processing {elrUri}")
                self.taxonomyJson["presentation"][elrUri] = {
                    "labels": {
                        "en": self.modelXbrl.roleTypeDefinition(elrUri, lang="en")
                    },
                }
                relSet = self.modelXbrl.relationshipSet(XbrlConst.parentChild, elrUri)
                roots = relSet.rootConcepts
                if len(roots) != 1:
                    self.cntlr.addToLog(
                        f"WARNING: Multi-root ELR will have an arbitrary presentation order. {elrUri} has {len(roots)} roots {' '.join(str(root.qname) for root in roots)}",
                        level=logging.WARNING,
                    )
                rows: list[tuple[int, QName, bool | str | None]] = []
                for root in roots:
                    rows.append((0, root.qname, None))
                    self.walkChildren(root, elrUri, relSet, rows, 1)
                self.taxonomyJson["presentation"][elrUri]["rows"] = [
                    (i, qname) for i, qname, _ in rows
                ]


def runTaxonomyInfo(
    cntlr: Cntlr,
    options: RuntimeOptions,
    modelXbrl: ModelXbrl,
    *args: Any,
    **kwargs: Any,
) -> None:
    start = time.perf_counter_ns()
    cntlr.addToLog(f"{PLUGIN_NAME} starting.")
    extractor = TaxonomyInfoExtractor(cntlr, options, modelXbrl)
    extractor.extract()
    if (jsonPath := getattr(options, "taxonomyDataFile", None)) is not None:
        writeDataFile(cntlr, jsonPath, "Taxonomy")
    if (jsonPath := getattr(options, "utrDataFile", None)) is not None:
        writeDataFile(cntlr, jsonPath, "UTR")
    elapsed = (time.perf_counter_ns() - start) / 1_000_000_000
    cntlr.addToLog(f"{PLUGIN_NAME} completed ({elapsed:,.2f} seconds elapsed).")


__pluginInfo__ = {
    "name": PLUGIN_NAME,
    "description": "Extracts information from a taxonomy",
    "license": "Apache-2.0",
    "version": "0.7",
    "author": "Stuart Rowan",
    "copyright": " Copyright :; EFRAG :: 2025",
    "CntlrCmdLine.Xbrl.Run": runTaxonomyInfo,
}
