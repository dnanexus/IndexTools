from csv import writer
from indextools.intervals import GenomeInterval
from indextools.regions import Regions
from indextools.utils import References
from . import tempdir


def test_targets():
    references = References([("chr1", 500)])

    ivls = [GenomeInterval("chr1", 25, 175)]

    with tempdir() as d:
        region_file = d / "regions.bed"
        with open(region_file, "wt") as out:
            w = writer(out, delimiter="\t")
            w.writerow(("chr1", "10", "100"))
            w.writerow(("chr1", "150", "200"))

        regions = Regions(targets=region_file)
        regions.init(references)
        assert list(regions.intersect(ivls)) == [
            GenomeInterval("chr1", 25, 100),
            GenomeInterval("chr1", 150, 175)
        ]
