import mireport
from mireport.taxonomy import VSME_ENTRY_POINT, getTaxonomy, listTaxonomies


def main() -> None:
    mireport.loadMetaData()
    print("Available taxonomies:", *listTaxonomies(), sep="\n\t")
    print(f"Ready to show {VSME_ENTRY_POINT} ")
    input("Press Enter to continue...")
    vsme = getTaxonomy(VSME_ENTRY_POINT)
    for group in vsme.presentation:
        print(f"{group.label} [{group.roleUri}]")
        for relationship in group.relationships:
            concept = relationship.concept
            print(
                "\t" * relationship.depth,
                concept.getStandardLabel(),
                f"[{concept.qname} {concept.dataType}]",
            )


if __name__ == "__main__":
    main()
