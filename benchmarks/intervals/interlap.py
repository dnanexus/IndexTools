"""
Implementation of Intervals using Brent Pedersen's InterLap.
"""
from enum import IntFlag
import itertools
import operator
from . import GenomeInterval, BasicGenomeInterval, Intervals
from typing import Iterable, Iterator, List, Sequence, Sized


class Side(IntFlag):
    """Side flag for use with interval searching.
    """
    LEFT = 1
    RIGHT = 2


class InterlapGenomeInterval(BasicGenomeInterval, Sized):
    def __len__(self) -> int:
        return self.end - self.start

    def __lt__(self, other) -> bool:
        if self.contig != other.contig:
            raise ValueError("Cannot compare intervals on different contigs")
        return self.start < other.start or (
            self.start == other.start and self.end < other.end
        )

    def __sub__(self, other):
        if self.start >= other.end:
            return (self.start + 1) - other.end
        elif self.end <= other.start:
            return self.end - (other.start + 1)
        else:
            return 0


class InterLapIntervals(Intervals):
    def __init__(self):
        self.interlaps = {}

    def update(self, intervals: Iterable[GenomeInterval]):
        for i in intervals:
            if i.contig not in self.interlaps:
                self.interlaps[i.contig] = InterLap()
            self.interlaps[i.contig].add(
                InterlapGenomeInterval(i.contig, i.start, i.end)
            )
        for il in self.interlaps.values():
            il.commit()

    def find(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        if ivl.contig not in self.interlaps:
            return []
        return list(
            BasicGenomeInterval(i.contig, i.start, i.end)
            for i in self.interlaps[ivl.contig].find(ivl)
        )

    def nearest_after(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        if ivl.contig not in self.interlaps:
            return []
        return list(
            BasicGenomeInterval(i.contig, i.start, i.end)
            for i in self.interlaps[ivl.contig].closest(ivl, Side.RIGHT)
        )


class InterLap:
    """Fast interval overlap testing. An InterLap is based on a sorted list
    of intervals. Resorting the list is only performed when `commit` is called.
    Overlap testing without first 'committing' any added intervals will probably
    yield incorrect results.

    See:
        Adapted from https://github.com/brentp/interlap.
    """

    def __init__(self):
        self._iset: List[InterlapGenomeInterval] = []
        self._maxlen = 0
        self._dirty = False

    def add(self, ivl: InterlapGenomeInterval):
        self._iset.append(ivl)
        self._dirty = True

    def commit(self) -> None:
        """Commit additions to this InterLap. This just means updating the
        _maxlen attribute and resorting the _iset list.
        """
        if self._dirty:
            self._resort()
            self._dirty = False

    def _resort(self):
        self._iset.sort()
        self._maxlen = max(len(r) for r in self._iset)

    def find(self, other: GenomeInterval) -> Iterator[InterlapGenomeInterval]:
        """Returns an iterable of elements that overlap `other` in the tree.
        """
        left = InterLap.binsearch_left_start(
            self._iset, other.start - self._maxlen, 0, len(self._iset)
        )
        right = InterLap.binsearch_right_end(self._iset, other.end, 0, len(self._iset))
        iopts = self._iset[left:right]
        yield from (s for s in iopts if InterLap.overlaps(s, other))

    def closest(
        self, other: GenomeInterval, side: int = Side.LEFT | Side.RIGHT
    ) -> Iterator[InterlapGenomeInterval]:
        """Returns an iterable of the closest interval(s) to `other`.

        Args:
            other: The interval to search.
            side: A bitwise combination of LEFT, RIGHT.

        Yields:
            If side == LEFT or RIGHT, the  single closest interval on the
            specified side is yielded.  If side == LEFT | RIGHT, all intervals
            that are equidistant on the left  and right side are yielded.
        """
        left = None
        if side & Side.LEFT:
            left = max(
                0,
                InterLap.binsearch_left_start(
                    self._iset, other.start - self._maxlen, 0, len(self._iset)
                )
                - 1,
            )

        right = None
        if side & Side.RIGHT:
            right = min(
                len(self._iset),
                InterLap.binsearch_right_end(
                    self._iset, other.end, 0, len(self._iset)
                )
                + 2,
            )

        if side == Side.LEFT | Side.RIGHT:
            # Expand candidates to include all left intervals with the same end
            # position and all right right intervals with the same start
            # position as the nearest.

            while left > 1 and self._iset[left].end == self._iset[left + 1].end:
                left -= 1

            while (
                right < len(self._iset)
                and self._iset[right - 1].start == self._iset[right].start
            ):
                right += 1

            iopts = self._iset[left:right]
            ovls = [s for s in iopts if InterLap.overlaps(s, other)]
            if ovls:
                # Yield all candidate intervals that overlap `other`
                yield from ovls
            else:
                #
                iopts = sorted([(abs(i - other), i) for i in iopts])
                _, g = next(iter(itertools.groupby(iopts, operator.itemgetter(0))))
                for _, ival in g:
                    yield ival
        else:
            if side == Side.LEFT:
                ivl = self._iset[left]
            else:
                ivl = self._iset[right - 1]
            if ivl != other:
                yield ivl

    @staticmethod
    def overlaps(ivl1: GenomeInterval, ivl2: GenomeInterval):
        return (
            ivl1.contig == ivl2.contig and
            ivl1.start < ivl2.end and
            ivl1.end > ivl2.start
        )

    @staticmethod
    def binsearch_left_start(
        intervals: Sequence[InterlapGenomeInterval], x: int, lo: int, hi: int
    ) -> int:
        """Like python's bisect_left, but finds the _lowest_ index where the value x
        could be inserted to maintain order in the list intervals.
        """
        while lo < hi:
            mid = (lo + hi) // 2
            f = intervals[mid]
            if f.start < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    @staticmethod
    def binsearch_right_end(
        intervals: Sequence[InterlapGenomeInterval], x: int, lo: int, hi: int
    ) -> int:
        """Like python's bisect_right, but finds the _highest_ index where the value
        x could be inserted to maintain order in the list intervals.
        """
        while lo < hi:
            mid = (lo + hi) // 2
            f = intervals[mid]
            if x < f.start:
                hi = mid
            else:
                lo = mid + 1
        return lo
