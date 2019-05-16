"""This is a complete example of how a BAM index can be used to estimate the "density"
of each genomic interval (16 kb size), where density is an approximate measure of the
size in bytes (which, in turn, is roughly correlated with the number of reads).

The primary use case is to partition a BAM file into N groups of intervals for parallel
processing a BAM file across N threads.

```
from intervals import get_bam_partitions

# Parallelize operations on a BAM file across many threads
threads = 32

# Get partitions of the BAM file that are roughly equal
partitions = get_bam_partitions(bam_file, num_groups=threads)

# Submit parallel jobs
for intervals in partitions:
    submit_job(process_bam, bam_file, intervals)
```
"""
from collections import Sized
import copy
from enum import IntFlag
import functools
import itertools
import operator
from typing import (
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from indextools.utils import OrderedSet

from ngsindex.utils import DefaultDict


BGZF_BLOCK_SIZE = 2 ** 16
"""Size of a BGZF block in bytes."""
INTERVAL_LEN = 2 ** 14
"""Length of an index interval in bases."""


# Type aliases
PositionTuple = Tuple[Union[int, str], int]
IntervalComparison = Tuple[int, int, float, float]
PositionComparison = Tuple[int, float, float]


class Side(IntFlag):
    """Side flag for use with interval searching.
    """

    LEFT = 1
    RIGHT = 2


IVL = TypeVar("IVL", bound="GenomeInterval")


class GenomeInterval(Sized):
    """An interval consists of a contig, start, and end position.
    Start and/or end may be None to signal that the interval extends to the
    end of the contig.

    Todo: How to merge annotations?
    """

    def __init__(
        self, contig: Union[int, str], start: int, end: int, **kwargs
    ) -> None:
        if start is None:
            start = 0
        if end <= start:
            raise ValueError(f"'end' must be >= 'start'; {end} <= {start}")
        self.contig = contig
        self.start = start
        self.end = end
        self.annotations = kwargs

    @property
    def region(self) -> str:
        return "{}:{}-{}".format(self.contig, self.start + 1, self.end)

    def __len__(self) -> int:
        return self.end - self.start

    def __contains__(self: IVL, other: Union[int, PositionTuple, IVL]) -> bool:
        """Does this interval overlap `other`?

        Args:
             other: Either an Interval or an int. If an int, assumed to be a
                position on the same contig as this sequence.
        """
        if isinstance(other, GenomeInterval):
            cmp = self.compare(other)
            return cmp[0] == 0 and abs(cmp[2]) > 0

        if isinstance(other, tuple):
            contig, pos = other
            if self.contig != contig:
                return False
        else:
            pos = cast(int, other)

        return self.start <= pos < self.end

    def __sub__(self: IVL, other: IVL) -> int:
        """Returns the distance between this interval and `other`. Negative
        value indicates that `other` is to the right, and positive value
        indicates that it is to the left.
        """
        self.contig_equal(other)
        return self.compare(other)[1]

    def __lt__(self: IVL, other: IVL) -> bool:
        contig, diff, overlap1, overlap2 = self.compare(other)
        if contig < 0:
            return True
        elif contig > 0:
            return False
        elif min(float(diff), overlap1) < 0:
            return True
        else:
            return overlap1 == 1 and overlap2 < 1

    def __eq__(self: IVL, other: IVL) -> bool:
        return (
            self.contig == other.contig
            and self.start == other.start
            and self.end == other.end
        )

    def __hash__(self) -> int:
        return hash((self.contig, self.start, self.end))

    def __repr__(self) -> str:
        return f"{self.contig}:{self.start}-{self.end}"

    def compare(self: IVL, other: IVL) -> IntervalComparison:
        """Rich comparison of intervals.

        Returns:
            A tuple consisting of 1) the comparison between this contig and
            other's contig; 2) the number of base pairs distance between
            this interval and `other`; and 3) the fraction of this interval
            overlapped by `other`, and 4) the fraction of `other` that overlaps
            this interval. Negative/positve numbers represents that one interval
            is to the left/right of the other.

        Examples:
            # End-inclusivity: a Interval is not end-inclusive, so an
            # interval whose end position is the same as the start position of
            # a second interval does *not* overlap that interval:
            i1 = Interval('chr1', 50, 100)
            i2 = Interval('chr1', 100, 200)
            cmp = i1.compare(i2)  # => (0, -1, 0, 0)
        """
        diff = 0
        overlap = 0

        if isinstance(other.contig, int):
            other_contig = cast(int, other.contig)
        else:
            other_contig = cast(str, other.contig)
        contig = self.contig
        if contig < other_contig:
            contig_cmp = -1
        elif contig > other_contig:
            contig_cmp = 1
        else:
            contig_cmp = 0

        if self.start >= other.end:
            diff = (self.start + 1) - other.end
        elif self.end <= other.start:
            diff = self.end - (other.start + 1)
        elif self.start >= other.start:
            overlap = min(self.end, other.end) - self.start
        else:
            overlap = other.start - self.end
        other_len = other.end - other.start

        return (
            contig_cmp,
            diff,
            min(1, overlap / len(self)),
            min(1, (-1 * overlap) / other_len)
        )

    def contig_equal(self: IVL, other: IVL) -> None:
        if self.contig != other.contig:
            raise ValueError(
                f"Intervals are on two different contigs: "
                f"{self.contig} != {other.contig}"
            )

    def add(self: IVL, other: IVL) -> IVL:
        """
        Add another interval to this one.

        Args:
            other: The interval to add.

        Returns:
            A new GenomeInterval.
        """
        cmp = self.compare(other)
        if cmp[0] != 0 or cmp[1] > 1:
            raise ValueError(
                f"Cannot merge non-overlapping/adjacent intervals {self}, {other}"
            )
        return GenomeInterval(
            self.contig, min(self.start, other.start), max(self.end, other.end),
            **self._merge_annotations(other)
        )

    def _merge_annotations(self: IVL, other: IVL) -> dict:
        annotations = copy.copy(self.annotations) or {}
        if "child_intervals" in annotations:
            annotations["child_intervals"].append(other)
        else:
            annotations["child_intervals"] = [self, other]
        return annotations

    def subtract(self: IVL, other: IVL = None) -> Tuple[Optional[IVL], Optional[IVL]]:
        self.contig_equal(other)
        if other not in self:
            raise ValueError(f"Intervals do not overlap: {self}, {other}")
        left = right = None
        if other.start > self.start:
            left = GenomeInterval(self.contig, self.start, other.start)
        if other.end < self.end:
            right = GenomeInterval(self.contig, other.end, self.end)
        return left, right

    def slice(self: IVL, start: Optional[int] = None, end: Optional[int] = None) -> IVL:
        if start is None or start < self.start:
            start = self.start
        if end is None or end > self.end:
            end = self.end
        return GenomeInterval(self.contig, start, end)

    @classmethod
    def intersect(cls: Type[IVL], ivl: IVL, *other: IVL) -> Iterator[IVL]:
        """
        Intersect `ivl` with `other` intervals.

        Args:
            ivl:
            *other:

        Yields:
            Intervals of the same type as `ivl`.
        """
        if len(other) == 0:
            raise ValueError("Must specify at least one other interval to intersect")

        other = list(sorted(other))

        ivl.check_contig(other[0])

        if len(other) == 1:
            other_list = other
        else:
            # First merge any of `other` intervals that are overlapping.
            other_list = []
            o1 = other[0]
            for o2 in other[1:]:
                cmp = o1.compare(o2)
                if cmp[0] != 0:
                    raise ValueError(
                        f"Cannot intersect intervals on different contigs; "
                        f"{o1.contig} != {o2.contig}"
                    )
                if cmp[1] <= 1:
                    o1 = o1.add(o2)
                else:
                    other_list.append(o1)
                    o1 = o2
            other_list.append(o1)

        for other_ivl in other_list:
            if other_ivl in ivl:
                yield ivl.slice(other_ivl)

    @classmethod
    def divide(cls: Type[IVL], ivl: IVL, *other: IVL) -> Iterator[IVL]:
        """
        Generate new intervals by subtracting other from `ivl`.

        Args:
            ivl:
            *other:

        Yields:
            Intervals of the same type as `ivl`.

        Raises:
            ValueError if any of `other` intervals do not overlap.
        """
        remaining = ivl

        for other in sorted(other):
            frag, remaining = remaining.subract(other)
            if frag:
                yield frag

        if remaining and len(remaining) > 0:
            yield remaining

    @classmethod
    def merge(cls: Type[IVL], intervals: Iterable[IVL]) -> IVL:
        """
        Merge overlapping GenomeIntervals.

        Args:
            intervals: Intervals to merge

        Returns:
            A new interval of the same type as `self`.

        Raises:
            ValueError if any of the intervals do not overlap.
        """
        intervals = list(sorted(intervals))
        merged = intervals[0]
        for ivl in intervals[1:]:
            merged = merged.add(ivl)
        return merged

    def as_bed3(self):
        """
        Returns this interval as a tuple in BED3 format.

        Returns:
            Tuple of length 3: (contig, start, end)
        """
        return self.contig, self.start, self.end

    def as_bed6(
        self, name: Optional[str] = None, value: Optional[int] = None, strand: str = "."
    ) -> Tuple:
        """
        Returns this interval as a tuple in BED6 format.

        Args:
            name:
            value:
            strand:

        Returns:
            Tuple of length 6: (contig, start, end, name, value, strand).
        """
        if name is None:
            name = str(self)
        if value is None:
            value = len(self)
        return self.contig, self.start, self.end, name, value, strand

    def as_bed_extended(self, annotation_names: Optional[Sequence[str]], **kwargs):
        """
        Returns this interval as a tuple with the first 6 columns being BED6 format
        and additional columns being annotations.

        Args:
            annotation_names: Optional list of annotation names for the extended
                columns. If specified, columns will be added in the specified order,
                and the empty value (".") used for missing columns. Otherwise, all
                annotations will be added in undetermined order.
            kwargs: Keyword arguments to `as_bed6`.

        Returns:
            Tuple of length 6+.
        """
        bed = self.as_bed6(**kwargs)
        if annotation_names:
            bed += tuple(self.annotations.get(name, ".") for name in annotation_names)
        elif self.annotations:
            bed += tuple(self.annotations.values())
        return bed

    def as_dict(self) -> dict:
        return {
            "contig": self.contig,
            "start": self.start,
            "end": self.end,
            "length": len(self),
            "region": self.region,
            "annotations": self.annotations
        }


class Intervals:
    """Collection of InterLaps (one per contig).

    Args:
        intervals: Iterable of GenomeIntervals.
        interval_type: Type of Interval that will be added. If None, is
            auto-detected from the first interval that is added.
        allows_overlapping: Whether overlapping intervals can be added,
            or if overlapping intervals are merged.
    """

    def __init__(
        self, intervals: Iterable[GenomeInterval] = (),
        interval_type: Type[GenomeInterval] = None,
        allows_overlapping: bool = True
    ) -> None:
        if interval_type is None:
            if intervals:
                intervals = list(intervals)
                interval_type = type(intervals[0])
            else:
                raise ValueError(
                    "Either 'interval_type' or 'intervals' must be specified."
                )
        self.interval_type = interval_type
        self.interlaps = DefaultDict(
            default=functools.partial(
                InterLap, interval_type=interval_type,
                allows_overlapping=allows_overlapping
            )
        )
        if intervals:
            self.add_all(intervals)

    @property
    def contigs(self) -> Sequence[str]:
        return tuple(self.interlaps.keys())

    def add_all(self, intervals: Iterable[GenomeInterval]) -> None:
        """Add all intervals from an iterable of GenomeIntervals.
        """
        modified = set()
        for interval in intervals:
            self.interlaps[interval.contig].add(interval)
            modified.add(interval.contig)
        for contig in modified:
            self.interlaps[contig].commit()

    def find(self, interval: GenomeInterval) -> Iterator[GenomeInterval]:
        """Find intervals that overlap `interval`.
        """
        contig = interval.contig
        if contig not in self.interlaps:
            return
        yield from self.interlaps[contig].find(interval)

    def intersect(self, interval: GenomeInterval) -> Iterator[GenomeInterval]:
        """Iterate over intersections with `interval`. Intersection is like
        find except that the yielded intervals include only the intersected
        portions.
        """
        contig = interval.contig
        if contig not in self.interlaps:
            return
        yield from self.interlaps[contig].intersect(interval)

    def intersect_all(
        self, intervals: Iterable[GenomeInterval]
    ) -> Iterator[GenomeInterval]:
        """Iterate over intersections with all `intervals`.
        """
        intersections = OrderedSet()
        for ivl in intervals:
            intersections.update(self.intersect(ivl))
        yield from intersections

    def closest(
        self, interval: GenomeInterval, side: int = Side.LEFT | Side.RIGHT
    ) -> Iterator[GenomeInterval]:
        """Find the closest interval(s) to `interval.
        """
        contig = interval.contig
        if contig not in self.interlaps:
            return
        yield from self.interlaps[contig].closest(other=interval, side=side)

    def __len__(self):
        return sum(len(ilap) for ilap in self.interlaps.values())

    def __contains__(self, interval: GenomeInterval) -> bool:
        """Returns True if `interval` intersects any intervals.
        """
        contig = interval.contig
        if contig not in self.interlaps:
            return False
        return interval in self.interlaps[contig]

    def __iter__(self) -> Iterator[GenomeInterval]:
        return itertools.chain(self.interlaps)


# TODO: replace InterLap with one of
#  * https://github.com/brentp/quicksect
#  * https://github.com/hunt-genes/ncls/
#  * https://biocore-ntnu.github.io/pyranges/
#  * https://github.com/lh3/cgranges


class InterLap:
    """Fast interval overlap testing. An InterLap is based on a sorted list
    of intervals. Resorting the list is only performed when `commit` is called.
    Overlap testing without first 'committing' any added intervals will probably
    yield incorrect results.

    Args:
        interval_type: Type of Interval that will be added. If None, is
            auto-detected from the first interval that is added.
        allows_overlapping: Whether overlapping intervals can be added,
            or if overlapping intervals are merged.

    See:
        Adapted from https://github.com/brentp/interlap.
    """

    def __init__(
        self, interval_type: Optional[Type[GenomeInterval]] = None,
        allows_overlapping: bool = True
    ) -> None:
        self.interval_type = interval_type
        self.allows_overlapping = allows_overlapping
        self._iset = []
        self._maxlen = 0
        self._dirty = False

    def add(
        self, intervals: Union[GenomeInterval, Sequence[GenomeInterval]],
        commit: Optional[bool] = None
    ):
        """Add a single (or many) Intervals to the tree.

        Args:
            intervals: An interval or sequence of intervals.
            commit: Whether these additions should be immediately committed.
        """
        if isinstance(intervals, GenomeInterval):
            intervals = [intervals]
        if self.interval_type is None:
            self.interval_type = type(intervals[0])
        if self.allows_overlapping:
            self._iset.extend(intervals)
            self._dirty = True
            if commit:
                self.commit()
        elif commit is False:
            raise ValueError(
                "Cannot set commit=False for InterLaps in which overlapping "
                "intervals are not allowed."
            )
        else:
            if self._dirty:
                self.commit()
            for ivl in intervals:
                overlapping = self.find(ivl)
                if overlapping:
                    ovl_list = list(overlapping)
                    for overlapping_ivl in ovl_list:
                        self._iset.remove(overlapping_ivl)
                    ovl_list.append(ivl)
                    ivl = GenomeInterval.merge(ovl_list)
                self._iset.append(ivl)
                self._resort()

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

    def __len__(self) -> int:
        """Return number of intervals."""
        return len(self._iset)

    def __iter__(self) -> Iterator[GenomeInterval]:
        return iter(self._iset)

    def __contains__(self, other: GenomeInterval) -> bool:
        """Indicate whether `other` overlaps any elements in the tree.
        """
        left = InterLap.binsearch_left_start(
            self._iset, other.start - self._maxlen, 0, len(self._iset)
        )
        # Use a shortcut, since often the found interval will overlap.
        max_search = 8
        if left == len(self._iset):
            return False
        for left_ivl in self._iset[left:(left + max_search)]:
            if left_ivl in other:
                return True
            if left_ivl.start > other.end:
                return False

        r = InterLap.binsearch_right_end(self._iset, other.end, 0, len(self._iset))
        return any(s in other for s in self._iset[(left + max_search):r])

    def find(self, other: GenomeInterval) -> Iterator[GenomeInterval]:
        """Returns an iterable of elements that overlap `other` in the tree.
        """
        left = InterLap.binsearch_left_start(
            self._iset, other.start - self._maxlen, 0, len(self._iset)
        )
        right = InterLap.binsearch_right_end(self._iset, other.end, 0, len(self._iset))
        iopts = self._iset[left:right]
        yield from (s for s in iopts if s in other)

    def intersect(self, other: GenomeInterval) -> Iterator[GenomeInterval]:
        """Like find, but the result is an iterable of new interval objects that
        cover only the intersecting regions.
        """
        for ivl in self.find(other):
            pos = sorted((ivl.start, ivl.end, other.start, other.end))
            yield self.interval_type(ivl.contig, pos[1], pos[2])

    def closest(
        self, other: GenomeInterval, side: int = Side.LEFT | Side.RIGHT
    ) -> Iterator[GenomeInterval]:
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
            ovls = [s for s in iopts if s in other]
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
    def binsearch_left_start(
        intervals: Sequence[GenomeInterval], x: int, lo: int, hi: int
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
        intervals: Sequence[GenomeInterval], x: int, lo: int, hi: int
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
