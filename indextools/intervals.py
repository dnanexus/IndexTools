from collections.abc import Sized
import copy
from enum import IntFlag
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

import cgranges as cr


BGZF_BLOCK_SIZE = 2 ** 16
"""Size of a BGZF block in bytes."""
INTERVAL_LEN = 2 ** 14
"""Length of an index interval in bases."""


# Type aliases
PositionTuple = Tuple[Union[int, str], int]
IntervalComparison = Tuple[int, int, float, float]
PositionComparison = Tuple[int, float, float]


class Side(IntFlag):
    """
    Side flag for use with interval searching.
    """

    LEFT = 1
    RIGHT = 2


IVL = TypeVar("IVL", bound="GenomeInterval")
BED3 = Tuple[str, int, int]
BED6 = Tuple[str, int, int, str, int, str]


class GenomeInterval(Sized):
    """
    An interval of a contig, consisting of a contig name, start position (
    zero-indexed), and end position (non-inclusive).

    Args:
        contig:
        start: Start position. May be `None` to signal that the interval extends to the
            beginning of the contig (i.e. position 0).
        end: End position.  May be `None` to signal that the interval extends to the
            end of the contig.

    Todo:
        How to merge annotations?
    """

    def __init__(self, contig: Union[int, str], start: int, end: int, **kwargs) -> None:
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
        """
        Rich comparison of intervals.

        Returns:
            A tuple consisting of 1) the comparison between this contig and
            other's contig; 2) the number of base pairs distance between
            this interval and `other`, where a zero value means they are overlapping;
            3) the fraction of this interval overlapped by `other`, and 4) the
            fraction of `other` that overlaps this interval. Negative/positve numbers
            that one interval is to the left/right of the other.

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
            min(1, (-1 * overlap) / other_len),
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
        if cmp[0] != 0 or abs(cmp[1]) > 1:
            raise ValueError(
                f"Cannot merge non-overlapping/adjacent intervals {self}, {other}"
            )
        return GenomeInterval(
            self.contig,
            min(self.start, other.start),
            max(self.end, other.end),
            **self._merge_annotations(other),
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

    def slice(
        self: IVL,
        other: Optional["GenomeInterval"] = None,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> IVL:
        """Creates a new interval with the bounds of the current interval restricted
        by those of `other`. If `start` or `end` are specified, they take precedence
        over `other`.

        Args:
            other:
            start:
            end:

        Returns:
            A new interval.
        """
        if other:
            self.contig_equal(other)
            if start is None:
                start = other.start
            if end is None:
                end = other.end
        if start is None or start < self.start:
            start = self.start
        if end is None or end > self.end:
            end = self.end
        return GenomeInterval(self.contig, start, end)

    @classmethod
    def intersect(cls: Type[IVL], ivl: IVL, other: Iterable[IVL]) -> Iterator[IVL]:
        """
        Intersect `ivl` with `other` intervals.

        Args:
            ivl:
            other:

        Yields:
            Intervals of the same type as `ivl`.
        """
        other_list = list(sorted(other))

        if len(other_list) == 0:
            raise ValueError("Must specify at least one other interval to intersect")

        ivl.contig_equal(other_list[0])

        if len(other_list) == 1:
            other_merged = other_list
        else:
            # First merge any of `other` intervals that are overlapping.
            other_merged = []
            o1 = other_list[0]
            for o2 in other_list[1:]:
                cmp = o1.compare(o2)
                if cmp[0] != 0:
                    raise ValueError(
                        f"Cannot intersect intervals on different contigs; "
                        f"{o1.contig} != {o2.contig}"
                    )
                if abs(cmp[2]) > 0:
                    o1 = o1.add(o2)
                else:
                    other_merged.append(o1)
                    o1 = o2
            other_merged.append(o1)

        for other_ivl in other_merged:
            if other_ivl in ivl:
                yield ivl.slice(other_ivl)

    @classmethod
    def divide(cls: Type[IVL], ivl: IVL, other: Iterable[IVL]) -> Iterator[IVL]:
        """
        Generates new intervals by subtracting `other` from `ivl`.

        Args:
            ivl:
            other:

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

    def as_bed3(self) -> BED3:
        """
        Returns this interval as a tuple in BED3 format.

        Returns:
            Tuple of length 3: (contig, start, end)
        """
        return self.contig, self.start, self.end

    def as_bed6(
        self, name: Optional[str] = None, value: Optional[int] = None, strand: str = "."
    ) -> BED6:
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

    def as_bed_extended(
        self, annotation_names: Optional[Sequence[str]], **kwargs
    ) -> tuple:
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
            "annotations": self.annotations,
        }


class Intervals:
    """
    Wrapper around a cranges that also stores `GenomeInterval`s by their
    (chromsome, start, end).

    Args:
        intervals: Iterable of GenomeIntervals.
        close: Whether to generate the index; if True, no additional intervals
            can be added. Ignored if `intervals` is None.
    """

    def __init__(
        self,
        intervals: Optional[Iterable[GenomeInterval]] = None,
        close: Optional[bool] = True
    ):
        self._cr = cr.cgranges()
        self._intervals = {}
        self._closed = False
        if intervals:
            self.add_all(intervals)
            if close:
                self.close()

    def add_all(self, intervals: Iterable[GenomeInterval]) -> None:
        """Add all intervals from an iterable of GenomeIntervals.

        Args:
            intervals: The intervals to add.
        """
        if self.closed:
            raise RuntimeError("Cannot add intervals after calling 'close()' method.")
        for interval in intervals:
            key = interval.as_bed3()
            # For now, prevent the addition of duplicate intervals. Could be changed
            # to dynamically create a list to contain duplicates.
            if key in self._intervals:
                raise ValueError(f"Cannot add duplicate interval {interval}")
            self._cr.add(*key)
            self._intervals[key] = interval

    def close(self) -> None:
        if not self.closed:
            self._cr.index()
            self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def find(self, interval: GenomeInterval) -> Iterator[GenomeInterval]:
        """Find intervals that overlap `interval`.

        Args:
            interval: The interval to search.

        Returns:
            An iterator over the overlapping intervals.
        """
        if not self.closed:
            raise RuntimeError("Cannot call 'find()' before calling 'close()'.")
        contig = interval.contig
        for start, end, _ in self._cr.overlap(*interval.as_bed3()):
            yield self._intervals[(contig, start, end)]
