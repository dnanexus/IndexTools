from typing import Optional, Sequence

import autoclick as ac
from xphyle import open_

from indextools.bed import BedInterval, iter_bed_interval_groups, iter_bed_intervals


def commands(
    template: str,
    primary: ac.ReadableFile,
    partitions_bed: ac.ReadableFile,
    group: bool = True,
    outfile: Optional[ac.WritableFile] = None,
    jinja2: bool = False
):
    """
    Generate a list commands, one per partition, given a template
    and a partition BED file.

    Args:
        template: The command template.
        primary: The primary file to split.
        partitions_bed: The partitions BED file.
        group: Whether to group intervals by name. If not, one command is generated
            for each interval rather than each partition.
        outfile: The output file - a text file with one command per line.
        jinja2: Whether the template is in Jinja2 syntax.
    """
    if jinja2:
        try:
            from jinja2 import Template
            tmpl = Template(template)
            tmpl_fn = tmpl.render
        except ImportError:
            raise ValueError("Jinja2 must be installed to use Jinja2 templates")
    else:
        tmpl_fn = template.format

    if group:
        itr = iter_bed_interval_groups(partitions_bed)

        def get_format_kwargs(ivls: Sequence[BedInterval]):
            return {
                "regions": ivls
            }
    else:
        itr = iter_bed_intervals(partitions_bed)

        def get_format_kwargs(ivl: BedInterval):
            return ivl.as_dict()

    with open_(outfile, "wt") as out:
        for rank, item in enumerate(itr):
            kwargs = {
                "primary": str(primary),
                "rank": rank,
            }
            kwargs.update(get_format_kwargs(item))
            print(tmpl_fn(**kwargs), file=out)
