from enum import Enum
import math
import statistics
from typing import Iterator, List, Optional, Sequence, Tuple, Union, Iterable

from indextools.intervals import GenomeInterval, IVL
from indextools.regions import Regions
from indextools.utils import References

from ngsindex import CoordinateIndex, Offset


BGZF_BLOCK_SIZE = 2 ** 16
"""Size of a BGZF block in bytes."""
INTERVAL_LEN = 2 ** 14
"""Length of an index interval in bases."""


class IntervalGrouping(Enum):
    """Interval grouping strategies.
    """

    NONE = 0
    """Do not group intervals."""
    CONSECUTIVE = 1
    """Group together equal numbers of consecutive intervals."""
    ROUND_ROBIN = 2
    """Distribute intervals to groups in a round-robin fashion."""


class VolumeInterval(GenomeInterval):
    def __init__(
        self, contig: str, start: int, end: int, volume: Optional[int] = None,
        **kwargs
    ):
        super().__init__(contig, start, end, **kwargs)
        self.volume = volume

    def get_volume(self, start: Optional[int] = None, end: Optional[int] = None) -> int:
        if not start or start < self.start:
            start = self.start
        if not end or end > self.end:
            end = self.end
        return int(math.ceil(((end - start) / len(self)) * self.volume))

    def add(self: "VolumeInterval", other: "VolumeInterval") -> "VolumeInterval":
        cmp = self.compare(other)
        if cmp[0] != 0:
            raise ValueError(f"Cannot merge non-overlapping intervals {self}, {other}")
        if cmp[3] == 1:
            return self
        elif cmp[2] == 1:
            return other
        else:
            if other.start < self.start:
                other_vol = other.get_volume(end=self.start)
            else:
                other_vol = other.get_volume(start=self.end)
            return VolumeInterval(
                self.contig, self.start, other.end, self.volume + other_vol,
                **self._merge_annotations(other)
            )

    def subtract(
        self: "VolumeInterval", other: "VolumeInterval" = None
    ) -> Tuple[Optional["VolumeInterval"], Optional["VolumeInterval"]]:
        self.contig_equal(other)
        if other not in self:
            raise ValueError(f"Intervals do not overlap: {self}, {other}")
        left = right = None
        if other.start > self.start:
            left = VolumeInterval(
                self.contig, self.start, other.start,
                self.get_volume(end=other.start)
            )
        if other.end < self.end:
            right = VolumeInterval(
                self.contig, other.end, self.end,
                self.get_volume(start=other.end)
            )
        return left, right

    def slice(
        self: "VolumeInterval", start: Optional[int] = None, end: Optional[int] = None
    ) -> "VolumeInterval":
        if start is None or start < self.start:
            start = self.start
        if end is None or end > self.end:
            end = self.end
        volume = self.get_volume(start, end)
        return VolumeInterval(self.contig, start, end, volume)

    def split(
        self: "VolumeInterval", num_pieces: Optional[int] = 2,
        target_volume: Optional[int] = None
    ) -> Iterator["VolumeInterval"]:
        """Break up an interval into smaller pieces.

        Args:
            num_pieces: Number of pieces in which to split the interval. Ignored if
                `target_volume` is set. Defaults to 2.
            target_volume: Target volume of the pieces.
        """
        if target_volume:
            num_pieces = int(math.ceil(self.volume / target_volume))

        # Yield one interval per piece
        total_length = len(self)
        piece_length = int(math.ceil(total_length / num_pieces))

        for ivl_start in range(self.start, self.end, piece_length):
            ivl_end = min(self.end, ivl_start + piece_length)
            ivl_vol = int(math.ceil(
                ((ivl_end - ivl_start) / total_length) * self.volume
            ))
            yield VolumeInterval(self.contig, ivl_start, ivl_end, ivl_vol)

    @staticmethod
    def merge_precomputed(intervals: Iterable[IVL], volume: int) -> "VolumeInterval":
        """
        Merge a group of intervals for which the total volume has already been
        computed.

        Args:
             intervals: Intervals to merge.
             volume: Precomputed volume.

        Returns:
            New VolumeInterval.
        """
        intervals = list(sorted(intervals))
        contig = intervals[0].contig
        start = intervals[0].start
        end = intervals[-1].end
        return VolumeInterval(contig, start, end, volume)

    def as_bed6(
        self, name: Optional[str] = None, value: Optional[int] = None, strand: str = "."
    ) -> Tuple:
        if value is None:
            value = self.volume
        return super().as_bed6(name, value, strand)

    def as_dict(self) -> dict:
        d = super().as_dict()
        d["volume"] = self.volume
        return d


class IndexInterval(VolumeInterval):
    """Mapping between a genomic interval and an offset in the linear index,
    including offset diffs from the previous interval.

    Args:
        ref_num: The reference index.
        ivl_num: The interval index.
        offset: The offset in the linear index.
        file_offset_diff: Difference in file offset from the previous IndexInterval.
        block_offset_diff: Difference in the block offset from the previous
            IndexInterval.
        contig_end: Whether this IndexInterval is the last one in a contig.
    """

    def __init__(
        self,
        references: References,
        ref_num: int,
        ivl_num: int,
        offset: Offset,
        file_offset_diff: int,
        block_offset_diff: int,
        contig_end: bool,
        **kwargs
    ) -> None:
        contig_name, contig_len = references.reference_list[ref_num]
        start = ivl_num * INTERVAL_LEN
        super().__init__(
            contig_name, start, min(contig_len, start + INTERVAL_LEN), **kwargs
        )
        self.ref_num = ref_num
        self.ivl_num = ivl_num
        self.offset = offset
        self.file_offset_diff = file_offset_diff
        self.block_offset_diff = block_offset_diff
        self.contig_end = contig_end

    @property
    def file_offset(self) -> int:
        return self.offset.file_offset

    @property
    def block_offset(self) -> int:
        return self.offset.block_offset

    def init_volume(self, compressed_block_size: int) -> int:
        """Estimate the volume of the interval (in bytes) and set the value of
        `self.volume`.

        First, divide ivl.file_offset_diff by compressed block size to estimate
        how many blocks are covered by the interval (minimum of 1). Then
        multiply by the uncompressed block size and add the block offset.

        Args:
            compressed_block_size: The estimated compressed size of a BGZF block.

        Returns:
            The estimated interval volume.
        """
        if self.file_offset_diff == 0:
            self.volume = self.block_offset_diff
        else:
            num_blocks = max(1.0, self.file_offset_diff / compressed_block_size)
            self.volume = int(math.ceil(
                (num_blocks * BGZF_BLOCK_SIZE) + self.block_offset_diff
            ))
        return self.volume

    def __repr__(self) -> str:
        return (
            f"{super().__repr__()} (ref_num={self.ref_num}, ivl_num={self.ivl_num}, " 
            f"offset={self.offset}, file_offset_diff={self.file_offset_diff}, "
            f"block_offset_diff={self.block_offset_diff})"
        )


# TODO: does the last partition need special handling (i.e. due to unmapped reads)?
# TODO: add annotations to the intervals with information about contained index
#  intervals.


def group_intervals(
    index: CoordinateIndex,
    references: References,
    num_groups: int,
    grouping: IntervalGrouping = IntervalGrouping.CONSECUTIVE,
    regions: Optional[Regions] = None,
    **kwargs,
) -> Union[Sequence[VolumeInterval], Sequence[Sequence[VolumeInterval]]]:
    """Determine equal-volume intervals, and then group adjacent intervals
    together to create `num_groups` equal volume groups.

    Args:
        index: An Index object.
        references: References object. Only used if the index file can't be
            resolved and we need to generate uniform volume intervals across
            the genome.
        num_groups: Number of groups to return.
        grouping: Strategy for grouping intervals
        regions: Restrict intervals to these regions.
        kwargs: Additional arguments passed through to `iter_index_intervals.`

    Returns:
        List of size `num_groups`. If grouping == NONE, each group is a single
        interval. Otherwise, each group is a list of intervals.
    """
    ivls = list(iter_index_intervals(index, references, **kwargs))

    if regions:
        ivls = list(regions.intersect(ivls))

    num_intervals = len(ivls)

    # With a large number of groups, there is the possibilty to have
    # fewer groups than intervals. Split all intervals in half until
    # num_intervals >= num_groups.
    while num_intervals < num_groups:
        new_intervals = []
        for ivl in ivls:
            new_intervals.extend(ivl.split())
        ivls = new_intervals
        num_intervals = len(ivls)

    if grouping == IntervalGrouping.NONE:
        return ivls
    elif grouping == IntervalGrouping.ROUND_ROBIN:
        # This code will distribute groups round-robin, so each partition will have
        # a large number of small groups
        return [ivls[n::num_groups] for n in range(num_groups)]
    elif grouping == IntervalGrouping.CONSECUTIVE:
        # This code will distribute groups blockwise, so each partition will have a
        # small number of large groups
        groups: List[List[VolumeInterval]] = [[] for _ in range(num_groups)]
        intervals_per_group = int(math.floor(num_intervals / num_groups))
        remainder = num_intervals - (intervals_per_group * num_groups)
        cur_group = 0
        cur_ivl: Optional[VolumeInterval] = None
        cur_group_ivl_count = 0
        target_ivl_count = intervals_per_group + (remainder > 0)

        for i, ivl in enumerate(ivls):
            if cur_ivl and ivl.contig == cur_ivl.contig:
                cur_ivl = cur_ivl.add(ivl)
            else:
                if cur_ivl:
                    groups[cur_group].append(cur_ivl)
                cur_ivl = ivl

            cur_group_ivl_count += 1

            if cur_group_ivl_count >= target_ivl_count and cur_group < (num_groups - 1):
                if cur_ivl:
                    groups[cur_group].append(cur_ivl)
                    cur_ivl = None
                cur_group += 1
                cur_group_ivl_count = 0
                target_ivl_count = intervals_per_group + (cur_group < remainder)

        if cur_ivl:
            groups[cur_group].append(cur_ivl)

        return groups

    raise ValueError(f"Unsupported grouping: {grouping}")


def iter_index_intervals(
    index: CoordinateIndex,
    references: References,
    batch_volume: int = None,
    batch_volume_coeff: float = 1.5,
) -> Iterator[VolumeInterval]:
    """Iterate over the intervals in the index and yield batch intervals that
    meet certain size criteria.

    Args:
        index: The pyngs.index.Index object.
        references: A list of reference sequences, in the same order they
            appear in the BAM header. Each item is a tuple (name, length).
        batch_volume: The target batch volume (in bytes). If None, this is
            estimated from the data.
        batch_volume_coeff: Multiplier for `batch_volume` to determine the
            maximum batch volume (1.5).

    Returns:
        Iterator over VolumeIntervals. Positions are zero-based, half-open,
        following the pysam convention.
    """
    ivls = index_to_intervals(index, references)

    file_offset_diffs = list(
        i.file_offset_diff for i in ivls if i.file_offset_diff > 0
    )
    if len(file_offset_diffs) > 0:
        # We assume that the median difference in block offsets is about the
        # average compressed size C of a single 64 KB block.
        compressed_block_size = int(statistics.median(file_offset_diffs))
    else:
        # If all the intervals are empty, it doesn't matter what the
        # compressed block size is - we just have to set it to something
        compressed_block_size = 1

    # Compute interval volumes
    interval_volumes = [ivl.init_volume(compressed_block_size) for ivl in ivls]

    # If the user did not specify a batch volume, we use the median of the
    # interval volumes.
    if not batch_volume:
        batch_volume = statistics.median(
            ivol for ivol in interval_volumes if ivol != 0
        )

    # Group together intervals smaller than batch volume, and break up intervals
    # larger than batch volume.
    group: List[IndexInterval] = []
    cur_ivl = ivls[0].ivl_num - 1
    cur_volume = 0
    max_batch_volume = batch_volume * batch_volume_coeff

    for interval, interval_volume in zip(ivls, interval_volumes):
        large_interval = interval_volume >= max_batch_volume

        # Yield the existing group if this interval is either large or not
        # consecutive with the previous interval.
        if group and (large_interval or (interval.ivl_num - 1) != cur_ivl):
            yield VolumeInterval.merge_precomputed(group, cur_volume)
            group = []
            cur_volume = 0

        if large_interval:
            # If the current interval is large, break it up and yield the pieces
            yield from interval.split(target_volume=batch_volume)

        else:
            # Yield if adding the current interval would make the existing
            # group too large
            if group and (cur_volume + interval_volume) > max_batch_volume:
                yield VolumeInterval.merge_precomputed(group, cur_volume)
                group = []
                cur_volume = 0

            group.append(interval)
            cur_volume += interval_volume
            cur_ivl = interval.ivl_num

            # Yield if this interval is the last one in a contig
            if interval.contig_end:
                yield VolumeInterval.merge_precomputed(group, cur_volume)
                group = []
                cur_volume = 0

    # Yield the last group
    if group:
        yield VolumeInterval.merge_precomputed(group, cur_volume)


def index_to_intervals(
    index: CoordinateIndex, references: References
) -> List[IndexInterval]:
    """Reduce an index to a list of intervals.

    Args:
        index: The index to convert.
        references:

    Returns:
        A list of IndexIntervals.
    """
    prev_interval = None
    prev_ref_num = None
    prev_ivl_num = None
    max_intervals = sum(int(math.ceil(r / INTERVAL_LEN)) for r in references.lengths)
    idxintervals: List[Optional[IndexInterval]] = [None] * max_intervals
    cur_interval = 0

    for ref_num, ref in enumerate(index.ref_indexes):
        num_ivls = ref.num_intervals
        if num_ivls == 0:
            continue

        # The first chunks of the contig are likely to be centromeric or telomeric,
        # and thus empty
        ref_intervals = ref.intervals
        first_ivl_num = 0
        while first_ivl_num < num_ivls and ref_intervals[first_ivl_num].empty:
            first_ivl_num += 1
        if first_ivl_num == num_ivls:
            # There are no reads on the contig
            continue

        # To compute the volume of each interval, we have to know the offsets of the
        # next interval. This always puts us one interval in arrears, which means we
        # have to take care with the intervals at the ends of contigs. e.g. we need
        # the first interval in chr2 to compute the volume of the last interval in
        # chr1, so the IndexInterval object we create from processing the first
        # interval in chr2 needs to have the ref and interval numbers left over at
        # the end of chr1.

        if prev_interval is None:
            prev_interval = ref_intervals[first_ivl_num]
            prev_ref_num = ref_num
            prev_ivl_num = first_ivl_num
            first_ivl_num += 1

        if first_ivl_num > 0:
            ref_intervals = ref_intervals[first_ivl_num:]

        for ivl_num, ivl in enumerate(ref_intervals, first_ivl_num):
            if ivl.empty:
                # the interval has no reads
                continue

            # Compute the difference in file and block offsets from the
            # previous interval. Remember that file offsets represent
            # compressed size and block offsets represent uncompressed size
            # from the start of the block.

            file_offset_diff = 0

            if ivl.file_offset != prev_interval.file_offset:
                # Compute the difference from the previous file offset if
                # we've moved to a new block.
                file_offset_diff = ivl.file_offset - prev_interval.file_offset

            # To compute the difference in block offsets, we need to
            # subtract the first part of the prev block (prev_block_offset)
            # and then add the offset into the current block.
            block_offset_diff = ivl.block_offset - prev_interval.block_offset

            # Finally, add the interval to the list
            idxintervals[cur_interval] = IndexInterval(
                references,
                prev_ref_num,
                prev_ivl_num,
                ivl,
                file_offset_diff,
                block_offset_diff,
                prev_ref_num != ref_num,
            )

            cur_interval += 1

            prev_interval = ivl
            prev_ref_num = ref_num
            prev_ivl_num = ivl_num

    # Add a dummy interval to cap the last contig
    if prev_ref_num is not None:
        idxintervals[cur_interval] = IndexInterval(
            references, prev_ref_num, prev_ivl_num, prev_interval, 0, 0, True
        )
        cur_interval += 1

    return idxintervals[:cur_interval]
