import enum
from functools import partial
import os
from typing import Optional, Tuple

import autoclick as ac
import pysam

from indextools.bed import BedInterval, iter_bed_interval_groups
from indextools.utils import References, split_path


class FeatureInclusion(enum.Enum):
    """
    Enumeration of options for determining which features to include for an
    interval.
    """
    OVERLAP = lambda start, end, read: (
        start < read.end and end > read.start
    )
    """Include any feature that overlaps at least one base of the interval."""
    CONTAIN = lambda start, end, read: (
        read.start >= start and read.end <= end
    )
    """Include any feature that is fully contained in the interval."""
    START = lambda start, end, read: (
        start <= read.start <= end
    )
    """Include any feature whose starting position is within the interval."""
    END = lambda start, end, read: (
        start <= read.end <= end
    )
    """Include any feature whose ending position is within the interval."""


def split(
    primary: ac.ReadableFile,
    partitions_bed: ac.ReadableFile,
    slop: Optional[Tuple[int, ...]] = None,
    features: FeatureInclusion = FeatureInclusion.OVERLAP,
    name_format: str = "{prefix}.{rank}.{ext}",
    output_dir: Optional[ac.WritableDir] = None,
    contig_sizes: Optional[ac.ReadableFile] = None
):
    """
    Split a primary file based on partitions in a BED file.

    Args:
        primary: The primary file to split.
        partitions_bed:
        slop: Padding to add on each side of each interval. If a single value,
            the same value is used for both the left and right side of the
            interval; otherwise the left and right slop can be specified separately.
        features:
        name_format:
        output_dir:
        contig_sizes: A file with the sizes of all the contigs in the index;
            only necessary if the primary file is not specified, or if it does not
            have sequence information in its header. This is a two-column tab-delimited
            file ({contig_name}\t{contig_size}).
    """
    if slop and len(slop) == 1:
        slop = slop[0], slop[0]

    path, prefix, exts = split_path(primary)
    ext = os.extsep.join(exts)
    if output_dir is None:
        output_dir = path

    if contig_sizes:
        references = References.from_file(contig_sizes)
    else:
        references = References.from_bam(primary)

    with pysam.AlignmentFile(primary, "rb") as bam:
        for rank, ivl_list in enumerate(iter_bed_interval_groups(partitions_bed)):
            partition_bam_filename = output_dir / name_format.format(
                rank=rank,
                prefix=prefix,
                ext=ext,
                **ivl_list[0].as_dict()
            )

            with pysam.AlignmentFile(partition_bam_filename, "wb", bam) as out:
                def write_ivl_reads(ivl: BedInterval):
                    contig, start, end = ivl.as_bed3()

                    if slop:
                        start = max(start - slop[0], 0)
                        end = min(end + slop[1], references.get_size(contig))

                    reads = bam.fetch(contig, start, end)

                    if features is not FeatureInclusion.OVERLAP:
                        reads = filter(partial(features.value, start, end), reads)

                    for read in reads:
                        out.write(read)

                for i in ivl_list:
                    write_ivl_reads(i)
