import sys
from collections import Counter

from lxml import etree

IX_NAMESPACE = "http://www.xbrl.org/2013/inlineXBRL"


def debug_ixbrl_element_counts(html_file_path):
    parser = etree.XMLParser()
    tree = etree.parse(html_file_path, parser)
    root = tree.getroot()

    ix_elements = root.xpath(f"//*[namespace-uri()='{IX_NAMESPACE}']")

    counts = Counter([etree.QName(el).localname for el in ix_elements])

    print(f"Inline XBRL elements found in {html_file_path}:")
    for tag, count in counts.most_common():
        print(f"  {tag}: {count}")

    facts = counts["nonFraction"] + counts["nonNumeric"]
    print(f"Total facts (nonFraction + nonNumeric): {facts}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/debug_ixbrl_counts.py path/to/file.html")
        sys.exit(1)

    debug_ixbrl_element_counts(sys.argv[1])
