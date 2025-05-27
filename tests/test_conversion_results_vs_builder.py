import pytest

from mireport.conversionresults import (
    ConversionResults,
    ConversionResultsBuilder,
    MessageType,
    Severity,
)


@pytest.fixture
def builder() -> ConversionResultsBuilder:
    builder = ConversionResultsBuilder(conversionId="test-id", consoleOutput=False)
    builder.addMessage("Conversion OK", Severity.INFO, MessageType.Conversion)
    builder.addMessage("XBRL Error", Severity.ERROR, MessageType.XbrlValidation)
    builder.addMessage("Excel Warning", Severity.WARNING, MessageType.ExcelParsing)
    builder.addMessage("Dev Note", Severity.INFO, MessageType.DevInfo)
    builder.addCellQueries([("Sheet1", 1, 1), ("Sheet2", 2, 2)])
    builder.addCellsWithData([("Sheet1", 1, 1)])
    return builder


def test_builder_to_results_conversion_preserves_data(builder):
    results: ConversionResults = builder.build()

    assert results.conversionId == builder.conversionId
    assert results.cellsQueried == len(builder.cellsPopulatedBuilder)
    assert results.cellsPopulated == len(builder.cellsPopulatedBuilder)
    assert len(results.messages) == len(builder.messages)
    assert isinstance(results, ConversionResults)


def test_user_vs_developer_message_filtering(builder):
    results = builder.build()

    user_messages = results.userMessages
    dev_messages = results.developerMessages

    # DevInfo should not be in user messages
    assert all(m.messageType != MessageType.DevInfo for m in user_messages)
    assert any(m.messageType == MessageType.DevInfo for m in dev_messages)


def test_conversion_successful_logic_matches_in_both(builder):
    expected_success = builder.conversionSuccessful

    results = builder.build()
    assert results.conversionSuccessful == expected_success


def test_xbrl_valid_flag():
    builder = ConversionResultsBuilder()
    # Add a non-XBRL error
    builder.addMessage("Something bad", Severity.ERROR, MessageType.Conversion)
    assert not builder.build().isXbrlValid

    builder2 = ConversionResultsBuilder()
    # Add an XBRL error — should also mark invalid
    builder2.addMessage("Invalid fact", Severity.ERROR, MessageType.XbrlValidation)
    assert not builder2.build().isXbrlValid

    builder3 = ConversionResultsBuilder()
    # No errors
    builder3.addMessage("All good", Severity.INFO, MessageType.XbrlValidation)
    assert builder3.build().isXbrlValid


def test_serialization_round_trip():
    builder = ConversionResultsBuilder(conversionId="abc123")
    builder.addMessage("Excel error", Severity.ERROR, MessageType.ExcelParsing)
    builder.addCellsWithData([("Sheet1", 3, 5)])
    results = builder.build()

    as_dict = results.toDict()
    rebuilt = ConversionResults.fromDict(as_dict)

    assert rebuilt.conversionId == results.conversionId
    assert rebuilt.cellsQueried == results.cellsQueried
    assert rebuilt.cellsPopulated == results.cellsPopulated
    assert rebuilt.conversionSuccessful == results.conversionSuccessful
    assert [m.toDict() for m in rebuilt.messages] == [
        m.toDict() for m in results.messages
    ]
