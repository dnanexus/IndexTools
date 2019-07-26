import pytest
from autoclick import ValidationError

from indextools.regions import parse_region, Region, Regions
from indextools.intervals import GenomeInterval
from indextools.utils import References


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



@pytest.mark.parametrize(
    "region_tuple,references,expected",
    [
        [
            ('chr1', 1, '*'),
            References([('chr1', 10000)]),
            GenomeInterval('chr1', 1, 10000)
        ],
        [
            ('chr1', 1, 2000),
            References([('chr1', 10000)]),
            GenomeInterval('chr1', 1, 2000)
        ]
    ],
)
def test__create_interval(region_tuple, references, expected):
    """Check that "*" is converted"""

    reg = Regions()
    reg.init(references)
    gi = reg._create_interval(region_tuple)
    assert gi == expected


def test__create_interval_ref_unfound():
    """Ensure that ValueError is raised if contig not found"""
    reg = Regions()
    ref = References([('chr1', 10000)]),
    reg.init(ref)

    with pytest.raises(ValueError) as e:
        reg._create_interval(('chr2', 1, '*'))
