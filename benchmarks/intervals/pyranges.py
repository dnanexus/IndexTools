"""
Implementation of Intervals for pyranges library.
"""
from typing import Iterable
from . import GenomeInterval, BasicGenomeInterval, Intervals
import pyranges as pr


class PyrangesIntervals(Intervals):
    def __init__(self):
        self.ranges = None

    def update(self, intervals: Iterable[GenomeInterval]):
        contigs, starts, ends = zip(*((i.contig, i.start, i.end) for i in intervals))
        self.ranges = pr.PyRanges(chromosomes=contigs, starts=starts, ends=ends)

    def find(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        ovl = self.ranges.overlap(
            pr.PyRanges(chromosomes=ivl.contig, starts=[ivl.start], ends=[ivl.end])
        )
        return (
            BasicGenomeInterval(contig, row["Start"], row["End"])
            for contig, df in ovl
            for _, row in df.iterrows()
        )

    def nearest_after(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        ovl = self.ranges.nearest(
            pr.PyRanges(chromosomes=ivl.contig, starts=[ivl.start], ends=[ivl.end]),
            how="next"
        )
        return (
            BasicGenomeInterval(contig, row["Start_b"], row["End_b"])
            for contig, df in ovl
            for _, row in df.iterrows()
        )
