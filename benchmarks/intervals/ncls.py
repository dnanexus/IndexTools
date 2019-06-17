"""
Implementation of Intervals for quicksect library.
"""
from . import GenomeInterval, Intervals, BasicGenomeInterval
from ncls import NCLS
from typing import Dict, Iterable
import numpy as np


class NclsIntervals(Intervals):
    def __init__(self):
        self.nclss: Dict[str, NCLS] = {}

    def update(self, intervals: Iterable[GenomeInterval]):
        temp = {}

        for ivl in intervals:
            if ivl.contig not in temp:
                temp[ivl.contig] = [[], []]
            temp[ivl.contig][0].append(ivl.start)
            temp[ivl.contig][1].append(ivl.end)

        for contig, (starts, ends) in temp.items():
            s = np.array(starts)
            e = np.array(ends)
            self.nclss[contig] = NCLS(s, e, s)

    def find(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        if ivl.contig not in self.nclss:
            return []
        return list(
            BasicGenomeInterval(ivl.contig, start, end)
            for start, end in zip(*self.nclss[ivl.contig].all_overlaps_both(
                np.array([ivl.start]), np.array([ivl.end]), np.array([0])
            ))
        )
