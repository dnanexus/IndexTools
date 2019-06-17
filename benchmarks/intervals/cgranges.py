from . import GenomeInterval, Intervals, BasicGenomeInterval
import cgranges as cr
from typing import Iterable


class CgrangesIntervals(Intervals):
    def __init__(self):
        self.cgr = cr.cgranges()

    def update(self, intervals: Iterable[GenomeInterval]):
        for ivl in intervals:
            self.cgr.add(ivl.contig, ivl.start, ivl.end)
        self.cgr.index()

    def find(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        return list(
            BasicGenomeInterval(ivl.contig, start, end)
            for start, end, _ in self.cgr.overlap(ivl.contig, ivl.start, ivl.end)
        )
