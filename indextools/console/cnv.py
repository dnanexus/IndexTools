import csv
import math
from pathlib import Path
from typing import Iterable, Optional, cast

import autoclick as ac
import cnvlib
from ngsindex import CoordinateIndex, IndexType, parse_index, resolve_index_file

from indextools.index import IndexInterval, iter_index_intervals
from indextools.regions import Regions
from indextools.utils import References


CNN_HEADER = (

)
EPSILON = math.pow(2, cnvlib.params.NULL_LOG2_COVERAGE)


def partition(
    primary: Optional[ac.ReadableFile] = None,
    index: Optional[ac.ReadableFile] = None,
    contig_sizes: Optional[ac.ReadableFile] = None,
    regions: Optional[Regions] = None
):
    """
    Call CNVs using CNVkit based on read depth estimated from the index.

    Args:
        primary:
        index:
        contig_sizes:
        regions:
    """
    if contig_sizes:
        references = References.from_file(contig_sizes)
    else:
        references = References.from_bam(primary)

    index_file = resolve_index_file(primary, IndexType.BAI, index)
    index = cast(CoordinateIndex, parse_index(index_file, IndexType.BAI))
    index_itr = iter_index_intervals(index, references)

    if regions:
        regions.init(references)
        target, antitarget = regions.split(index_itr)
        write_cnn(antitarget, )
    else:
        target = index_itr

    write_cnn(target, )


def write_cnn(ivls: Iterable[IndexInterval], output_file: Path, header: bool = True):
    with open(output_file, "wt") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        if header:
            writer.writerow(CNN_HEADER)
        for i, ivl in enumerate(ivls):
            writer.writerow((
                ivl.contig,
                ivl.start,
                ivl.end,
                f"bin_{i}",
                math.log2(ivl.volume + EPSILON),
                ivl.volume
            ))
