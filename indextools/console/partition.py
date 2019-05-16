"""
TODO: allow for custom partition naming
"""
import pathlib
from typing import Callable, List, Optional, cast

from indextools.bed import write_intervals_bed
from indextools.index import IntervalGrouping, group_intervals
from indextools.intervals import GenomeInterval
from indextools.regions import Regions
from indextools.utils import References, split_path

import autoclick as ac
from ngsindex import IndexType, CoordinateIndex, resolve_index_file, parse_index


def partition(
    primary: Optional[ac.ReadableFile] = None,
    index: Optional[ac.ReadableFile] = None,
    partitions: int = 100,
    grouping: IntervalGrouping = IntervalGrouping.CONSECUTIVE,
    outfile: Optional[ac.WritableFile] = None,
    annotation: Optional[List[str]] = None,
    contig_sizes: Optional[ac.ReadableFile] = None,
    regions: Optional[Regions] = None,
    bgzip_outfile: bool = True,
    index_outfile: bool = True,
):
    """
    Determine a partitioning of the input file, such that all partitions are roughly
    the same volume.

    Args:
        primary: The file to partition.
        index: The index of the primary file.
        partitions: The number of partitions to generate.
        grouping: How to group intervals: 'NONE' - do not group intervals;
            'CONSECUTIVE' - group consecutive intervals (including intervals
            on consecutive contigs); 'ROUND_ROBIN' - assign intervals to
            partitions in round-robin fashion.
        outfile: The output partition BED file. Defaults to '{file}_partitions.bed.gz'.
        annotation: Names of annotations to add in columns 7+ of the output BED file.
            Currently accepted values are: 'child_lengths' (comma-delimited list of
            lengths in bp of child intervals), 'child_volumes' (comma-delimited list
            of volumes of child intervals).
        contig_sizes: A file with the sizes of all the contigs in the index;
            only necessary if the primary file is not specified, or if it does not
            have sequence information in its header. This is a two-column tab-delimited
            file ({contig_name}\t{contig_size}).
        regions: Regions to which the partitions are restricted.
        bgzip_outfile: Bgzip the output file. Set to False if 'outfile' is specified
            and it does not end with '.gz'.
        index_outfile: Tabix index the output file. Set to False if bgzip is disabled.
    """
    index_file = resolve_index_file(primary, IndexType.BAI, index)

    if outfile is None:
        prefix = split_path(primary)[1]
        outfile_name = f"{prefix}.bed"
        if bgzip_outfile:
            outfile_name += ".gz"
        outfile = pathlib.Path.cwd() / outfile_name
    elif outfile.suffix != ".gz":
        bgzip_outfile = False

    if not bgzip_outfile:
        index_outfile = False

    if contig_sizes:
        references = References.from_file(contig_sizes)
    else:
        references = References.from_bam(primary)

    partition_intervals = group_intervals(
        cast(CoordinateIndex, parse_index(index_file, IndexType.BAI)),
        references,
        num_groups=partitions,
        grouping=grouping,
        regions=regions
    )

    extra_columns = None
    if annotation:
        fns = [ANNOTATION_FUNCTIONS[name] for name in annotation]

        def extra_columns(ivl: GenomeInterval) -> tuple:
            return tuple(fn(ivl) for fn in fns)

    write_intervals_bed(
        partition_intervals,
        outfile,
        bgzip=bgzip_outfile,
        index=index_outfile,
        extra_columns=extra_columns
    )


def child_apply(fn: Callable):
    def _apply(ivl: GenomeInterval):
        children = ivl.annotations.get("child_intervals", None)
        if children:
            return ",".join(str(fn(child)) for child in children)
        else:
            return "."
    return _apply


ANNOTATION_FUNCTIONS = {
    "child_lengths": child_apply(lambda child: len(child)),
    "child_volumes": child_apply(lambda child: child.volume)
}
