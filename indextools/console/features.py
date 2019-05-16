from typing import Optional

import autoclick as ac
import pysam

from indextools.bed import GenomeInterval, iter_bed_intervals, write_intervals_bed
from indextools.utils import replace_suffix


def features(
    primary: ac.ReadableFile,
    partitions_bed: ac.ReadableFile,
    outfile: Optional[ac.WritableFile] = None,
    bgzip_outfile: bool = True,
    index_outfile: bool = True
):
    """
    Counts the number of features per partition, given a primary file and a BED file
    (such as output by the `partition` command).

    Args:
        primary: The primary file.
        partitions_bed: The partition BED file.
        outfile: The output BED file. If not specified, the primary filename is used
            with a '_features' suffix.
        bgzip_outfile: Bgzip the output file. Set to False if 'outfile' is specified
            and it does not end with '.gz'.
        index_outfile: Tabix index the output file. Set to False if bgzip is disabled.
    """
    if outfile is None:
        suffix = "_features.bed"
        if bgzip_outfile:
            suffix += ".gz"
        outfile = replace_suffix(primary, suffix)

    partitions_iter = iter_bed_intervals(partitions_bed)

    with pysam.AlignmentFile(primary, "rb") as bam:
        def count_interval(ivl: GenomeInterval):
            def check_read(read):
                """Check that a read starts within `ivl`.
                """
                return ivl.start <= read.reference_start < ivl.end

            count = bam.count(*ivl.as_bed3(), read_callback=check_read)

            return count,

        write_intervals_bed(
            partitions_iter, outfile, extra_columns=count_interval,
            bgzip=bgzip_outfile, index=index_outfile
        )
