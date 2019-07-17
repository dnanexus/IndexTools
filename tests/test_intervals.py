from indextools.intervals import Intervals, GenomeInterval


def test_intervals():
    intervals = Intervals()
    intervals.add_all([
        GenomeInterval("chr1", 0, 10),
        GenomeInterval("chr1", 5, 15),
        GenomeInterval("chr2", 3, 7)
    ])
    results = list(sorted(intervals.find(GenomeInterval("chr1", 3, 7))))
    assert len(results) == 2
    assert all(r.contig == "chr1" for r in results)
    assert results[0].as_bed3() == ("chr1", 0, 10)
    assert results[1].as_bed3() == ("chr1", 5, 15)
