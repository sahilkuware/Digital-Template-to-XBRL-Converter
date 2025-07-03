import subprocess
import sys
from pathlib import Path

import pytest
from lxml import etree

IX_NAMESPACE = "http://www.xbrl.org/2013/inlineXBRL"

TEST_CASES = [
    ("tests/data/VSME-Digital-Template-Sample-1.0.0.xlsx", 139),
    ("tests/data/VSME-Digital-Template-Sample-1.0.xlsx", 139),
    ("tests/data/vsme-unit-test-v1.0.0.xlsx", 159),
]

def format_subprocess_output(result: subprocess.CompletedProcess) -> str:
    """Format stdout and stderr of a subprocess result for debug output."""
    return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

@pytest.mark.parametrize("input_file,expected_fact_count", TEST_CASES)
def test_parse_and_ixbrl_fact_count(input_file, expected_fact_count, tmp_path):
    input_path = Path(input_file)
    output_file = tmp_path / "output.html"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/parse-and-ixbrl.py",
            "--skip-validation", # Skip XBRL validation as we're testing fact production in this test
            str(input_path),
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed for {input_file}:\n{format_subprocess_output(result)}"

    assert output_file.exists(), (
        f"Output HTML file was not created for {input_file}.\n"
        f"{format_subprocess_output(result)}"
    )

    parser = etree.XMLParser()
    tree = etree.parse(str(output_file), parser)
    root = tree.getroot()

    ns = {"ix": IX_NAMESPACE}

    fact_elements = root.xpath("//ix:nonNumeric | //ix:nonFraction", namespaces=ns)

    actual_fact_count = len(fact_elements)

    assert actual_fact_count == expected_fact_count, (
        f"For {input_file}, expected {expected_fact_count} facts but found {actual_fact_count}.\n"
        f"{format_subprocess_output(result)}"
    )
