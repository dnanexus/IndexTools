"""IndexTools command line interface.
"""
from idxtools.console import (
    partition,
    features,
    split,
    commands
)
from idxtools.regions import Regions, parse_region

import autoclick as ac


COMMON_SHORT_NAMES = {
    "primary": "i",
    "index": "I",
    "partitions_bed": "p",
    "pair": "P",
    "outfile": "o",
    "contig_sizes": "z",
    "region": "r",
    "exclude_region": "R",
    "contig": "c",
    "exclude_contig": "C",
    "targets": "t",
    "exclude_targets": "T"
}


def merge_short_names(d):
    sn = dict(COMMON_SHORT_NAMES)
    sn.update(d)
    return sn


# Set global options
ac.set_global("infer_short_names", False)
ac.set_global("add_composite_prefixes", False)


# Register conversion functions
ac.conversion(decorated=parse_region)
ac.composite_type(
    decorated=Regions,
    short_names=COMMON_SHORT_NAMES
)


@ac.group()
def idxtools():
    pass


# Partition genomic regions based on read density estimated
# from an index.
idxtools.command(
    decorated=partition.partition,
    types={
        "slop": ac.DelimitedList(int)
    },
    validations={
        ("primary", "contig_sizes"): ac.defined_ge(1)
    },
    short_names=merge_short_names({
        "partitions": "n",
        "grouping": "g"
    })
)


# Count the features (e.g. reads, variants) in a primary file
# within partitions (e.g. output by the 'partition' command).
idxtools.command(
    decorated=features.features
)


# Split a primary file (e.g. BAM, VCF) into chunks based on
# a partition BED file (e.g. output by the 'partition' command).
idxtools.command(
    decorated=split.split,
    types={
        "slop": ac.DelimitedList(int)
    },
    validations={
        "slop": ac.SequenceLength(1, 2)
    },
    short_names=merge_short_names({
        "slop": "s"
    })
)


# Generate a list commands, one per partition, given a template
# and a partition BED file (e.g. output by the 'partition' command).
idxtools.command(
    decorated=commands.commands
)


#
# idxtools.command(
#     decorated=run
# )
