import pytest
from autoclick import ValidationError

from indextools.regions import parse_region


@pytest.mark.parametrize(
    "region_str,expected_tuple",
    [
        ("chr1:100-10000", ("chr1", 99, 10000)),
        ("chr1:100-*", ("chr1", 99, "*")),
        ("1:100-*", ("1", 99, "*")),
        ("1:100", ("1", 99, 100)),
    ],
)
def test_parse_region(region_str, expected_tuple):
    """Ensure that '*' works and that start has a offset by -1"""
    result = parse_region(region_str)
    assert result == expected_tuple


@pytest.mark.parametrize(
    "region_str,exception_type,error_message_content",
    [
        ("chr1:0-10000", ValidationError, "start must be >= 1"),
        ("chr1:1000-0", ValidationError, "start must be <= end"),
        ("chr1:0-wrong", ValueError, "invalid literal for int() with base 10"),
    ],
)
def test_parse_region_raises(region_str, exception_type, error_message_content):
    """Ensure that correct expcetions are raised when region_str is incorrect"""

    with pytest.raises(exception_type) as e:
        assert parse_region(region_str)
    assert error_message_content in str(e.value)
