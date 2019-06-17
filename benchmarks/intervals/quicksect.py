"""
Implementation of Intervals for quicksect library.
"""
from . import GenomeInterval, Intervals, BasicGenomeInterval
from quicksect import Interval, IntervalTree
from typing import Dict, Iterable


class QuicksectInterval(GenomeInterval):
    def __init__(self, ivl: Interval):
        self._ivl = ivl

    @property
    def contig(self) -> str:
        return self._ivl.data

    @property
    def start(self) -> int:
        return self._ivl.start

    @property
    def end(self) -> int:
        return self._ivl.end


class QuicksectIntervals(Intervals):
    def __init__(self):
        self.trees: Dict[str, IntervalTree] = {}

    def update(self, intervals: Iterable[GenomeInterval]):
        for ivl in intervals:
            if ivl.contig not in self.trees:
                self.trees[ivl.contig] = IntervalTree()
            self.trees[ivl.contig].add(ivl.start, ivl.end, ivl.contig)

    def find(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        if ivl.contig not in self.trees:
            return []
        return list(
            BasicGenomeInterval(i.data, i.start, i.end)
            for i in self.trees[ivl.contig].search(ivl.start, ivl.end)
        )
