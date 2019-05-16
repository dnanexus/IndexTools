from contextlib import contextmanager
import csv
import _csv
from pathlib import Path
import subprocess
from typing import Callable, Iterable, Iterator, Optional, Sequence, Union, Tuple

from indextools.intervals import GenomeInterval

from xphyle import STDOUT, open_
from xphyle.utils import read_delimited


class BedInterval(GenomeInterval):
    def __init__(
        self, contig: Union[int, str], start: int, end: int,
        name: Optional[str] = None, value: Optional[int] = None,
        strand: Optional[str] = ".", other: Optional[Sequence[str]] = None
    ) -> None:
        super().__init__(contig, start, end)
        self.name = name
        self.value = value
        self.strand = strand
        self.other = other

    @staticmethod
    def from_row(row: Sequence[str]):
        contig = row[0]
        start = int(row[1])
        end = int(row[2])
        name = row[3] if len(row) > 3 else None
        value = row[4] if len(row) > 4 else None
        strand = row[5] if len(row) > 5 else "."
        other = row[6:] if len(row) > 6 else None
        return BedInterval(contig, start, end, name, value, strand, other)

    def as_bed6(
        self, name: Optional[str] = None, value: Optional[int] = None,
        strand: str = None
    ) -> Tuple:
        return super().as_bed6(
            name or self.name, value or self.value, strand or self.strand
        )

    def as_dict(self) -> dict:
        d = super().as_dict()
        if self.name:
            d["name"] = self.name
        if self.value:
            d["value"] = self.value
        if self.strand:
            d["strand"] = self.strand
        if self.other:
            d["other"] = self.other
        return d


def iter_bed_intervals(bed_file: Path) -> Iterator[BedInterval]:
    """
    Iterate over intervals in a BED file.

    Args:
        bed_file: Path to the BED file.

    Returns:
        Iterator over :class:`GenomeInterval` objects.
    """
    for row in read_delimited(bed_file):
        yield BedInterval.from_row(row)


def iter_bed_interval_groups(
    bed_file: Path, assume_collated: bool = False
) -> Iterator[Sequence[BedInterval]]:
    """
    Iterate over groups of intervals in a BED file, where a group is a set of
    consecutive intervals that have the same name (i.e. value in column 4).

    Args:
        bed_file: Path to the BED file.
        assume_collated: Whether to assume that all intervals with the same name
            are consecutive in the BED file.

    Returns:
        Iterator over sequences of :class:`GenomeInterval` objects.
    """
    ivls = iter_bed_intervals(bed_file)

    if not assume_collated:
        ivls = sorted(ivls, key=lambda i: i.name)

    cur_group = []

    for ivl in ivls:
        if not cur_group or ivl.name == cur_group[-1].name:
            cur_group.append(ivl)
        else:
            yield cur_group
            cur_group = []

    yield cur_group


@contextmanager
def bed_writer(
    outfile: Path, bgzip: bool = True, index: bool = True
) -> Iterator[_csv.writer]:
    """
    Context manager that provides a writer for rows in a BED file.

    Args:
        outfile: The BED file to write.
        bgzip: Whether to bgzip the output file after it is closed.
        index: Whether to index the output file (must be bgzipped).

    Yields:
        A csv.writer object.
    """
    with open_(outfile, "wt", compression=("bgzip" if bgzip else None)) as out:
        writer = csv.writer(out, delimiter="\t")
        yield writer

    if bgzip and index:
        # TODO: replace this with dxpy.sugar.run
        subprocess.check_call(["tabix", "-p", "bed", str(outfile)])


def write_intervals_bed(
    ivls: Union[Iterable[GenomeInterval], Iterable[Sequence[GenomeInterval]]],
    outfile: STDOUT, name_pattern: str = "Partition_{group}",
    extra_columns: Optional[Callable[[GenomeInterval], tuple]] = None,
    bgzip: bool = True, index: bool = True
):
    """
    Write GenomeIntervals to a BED file.

    Args:
        ivls: The intervals to write to BED format.
        outfile: The output BED file.
        name_pattern: Pattern for naming rows in the BED file. This can be a format
            string with placeholders 'group' and 'row' having the current group and
            row numbers.
        extra_columns: Optional function that creates extra columns for each row
            in the bed file. Must return a tuple of the same length for every row.
            Missing values should be represented as "." rather than empty string or
            None.
        bgzip: Whether to bgzip the output file.
        index: Whether to tabix index the output file (must be bgzipped).
    """
    with bed_writer(outfile, bgzip, index) as bed:
        row_ctr = 1
        for group_ctr, group in enumerate(ivls, 1):
            def writewrow(ivl: GenomeInterval):
                name = name_pattern.format(group=group_ctr, row=row_ctr)
                row = ivl.as_bed6(name)
                if extra_columns:
                    row += extra_columns(ivl)
                bed.writerow(row)

            if isinstance(group, Sequence):
                for group_ivl in group:
                    writewrow(group_ivl)
                    row_ctr += 1
            else:
                writewrow(group)
                row_ctr += 1


def annotations_extra_columns(
    names: Optional[Sequence[str]] = None
) -> Callable[[GenomeInterval], tuple]:
    """
    Creates a function that can be passed as the `extra_columns` argument to
    `write_intervals_bed` that generates extra columns from the interval's
    annotations.

    Args:
        names: Optional, the names of the annotations to extract as extra columns.

    Returns:
        Callable
    """
    def extra_columns(ivl: GenomeInterval):
        return ivl.as_bed_extended(names)
    return extra_columns
