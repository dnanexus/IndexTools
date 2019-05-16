from pathlib import Path
import re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union

from .bed import iter_bed_intervals
from .intervals import GenomeInterval, Intervals, IVL
from .utils import References

from autoclick import ValidationError


REGION_RE = re.compile(r"[:-]")
Region = Tuple[str, int, Union[str, int]]


def parse_region(region_str: str) -> Region:
    """
    Convert a region string into an interval.

    Args:
        region_str: Region string, such as 'chr1:100-1000' or '5:0-*'.

    Returns:
        A tuple (chr, start, end), where end may be an integer or '*' indicating the
        end of the contig.
    """
    parts = REGION_RE.split(region_str)
    if len(parts) == 1:
        return parts[0], 0, "*"
    else:
        contig = parts[0]
        start = int(parts[1])
        if len(parts) == 2:
            end = start
        else:
            end = int(parts[2])
        if start <= 0:
            raise ValidationError(
                f"Invalid region interval {region_str}: start must be >= 1"
            )
        start -= 1
        if start >= end:
            raise ValidationError(
                f"Invalid region interval {region_str}: start must be <= end"
            )
        return contig, start, end


# TODO: add an invert option - not sure if makes sense to add this to the
#  constructor or make it a paramter to the methods.


class Regions:
    """
    Collection of genome regions.

    Args:
        region: A region string, e.g. chr1:10-100.
        exclude_region: A region to exclude.
        contig: A contig string (name, range, or macro).
        exclude_contig: A contig to exclude.
        targets: A BED file with targets to include.
        exclude_targets: A BED file with targets to exclude.
    """
    def __init__(
        self,
        region: Optional[List[Region]] = None,
        exclude_region: Optional[List[Region]] = None,
        contig: Optional[List[str]] = None,
        exclude_contig: Optional[List[str]] = None,
        targets: Optional[Path] = None,
        exclude_targets: Optional[Path] = None
    ):
        self._include_regions = region
        self._exclude_regions = exclude_region
        self._include_contigs = contig
        self._exclude_contigs = exclude_contig
        self._include_targets = targets
        self._exclude_targets = exclude_targets
        self._references = None
        self._include_intervals = None
        self._exclude_intervals = None

    def init(
        self, references: References, macros: Optional[Dict[str, List[str]]] = None
    ):
        self._references = references

        if self._include_regions or self._include_contigs or self._include_targets:
            self._include_intervals = self._create_region_intervals(
                self._include_regions,
                self._include_contigs,
                self._include_targets,
                macros
            )

        if self._exclude_regions or self._exclude_contigs or self._exclude_targets:
            self._exclude_intervals = self._create_region_intervals(
                self._exclude_regions,
                self._exclude_contigs,
                self._include_targets,
                macros
            )

    def _create_region_intervals(
        self,
        regions: Optional[List[Region]] = None,
        contigs: Optional[List[str]] = None,
        targets: Optional[Path] = None,
        macros: Optional[Dict[str, List[str]]] = None
    ) -> Intervals:
        intervals = Intervals(allows_overlapping=False)

        if regions:
            intervals.add_all(self._create_interval(ivl) for ivl in regions)

        if contigs:
            if macros:
                while True:
                    expanded = set()
                    done = True
                    for contig in contigs:
                        if contig in macros:
                            expanded.update(macros[contig])
                            done = False
                    contigs = list(expanded)
                    if done:
                        break

            matchers = []

            for contig in contigs:
                if "-" in contig:
                    start_str, end_str = contig.split("-")
                    i = 0
                    while start_str[i].isalpha():
                        i += 1
                    start = float(start_str[i:])
                    end = float(end_str[i:])
                    matchers.append(lambda c: start <= float(c[i:]) <= end)
                else:
                    matchers.append(re.compile(contig).fullmatch)

            contigs = set()

            for ref in self._references.names:
                for matcher in matchers:
                    if matcher(ref):
                        contigs.add(ref)
                        break

            if contigs:
                intervals.add_all(
                    GenomeInterval(contig, 0, self._references[contig])
                    for contig in contigs
                )

        if targets:
            intervals.add_all(iter_bed_intervals(targets))

        return intervals

    def _create_interval(self, region: Region) -> GenomeInterval:
        contig, start, end = region
        if end == "*":
            if contig in self._references:
                end = self._references[contig]
            else:
                raise ValueError(
                    f"Contig {contig} not found in references"
                )
        return GenomeInterval(contig, start, end)

    def allows(self, interval: GenomeInterval) -> bool:
        """

        Args:
            interval:

        Returns:
            True if 'interval' is fully contained within an included region (if any)
            and does not overlap any excluded region (if any).
        """

        if self._include_intervals:
            contained = False
            overlapping = self._include_intervals.find(interval)
            for ivl in overlapping:
                if interval.compare(ivl)[2] == 1:
                    contained = True
        else:
            contained = True

        if not contained or (
            self._exclude_intervals and interval in self._exclude_intervals
        ):
            return False

        return True

    def iter_allowed(self) -> Iterator[GenomeInterval]:
        if self._include_intervals:
            interval_itr = self._include_intervals
        else:
            interval_itr = (
                GenomeInterval(ref, 0, self._references[ref])
                for ref in self._references.names
            )
        if self._exclude_intervals:
            for ivl in interval_itr:
                overlapping = self._exclude_intervals.find(ivl)
                if overlapping:
                    yield from GenomeInterval.divide(ivl, overlapping)
                else:
                    yield ivl
        else:
            yield from interval_itr

    def intersect(self, intervals: Iterable[IVL]) -> Iterator[IVL]:
        """
        Constrain intervals to the regions specified by this Regions object.

        Args:
            intervals: The intervals to constrain.

        Yields:
            Intervals that are in the intersection of `intervals` and this set
            of regions.
        """
        for ivl in intervals:
            intersection = []

            if self._include_intervals:
                incl_overlapping = self._include_intervals.find(ivl)
                if incl_overlapping:
                    intersection = GenomeInterval.intersect(ivl, incl_overlapping)
            else:
                intersection = [ivl]

            if self._exclude_intervals:
                for subivl in intersection:
                    excl_overlapping = self._exclude_intervals.find(subivl)
                    if excl_overlapping:
                        yield from GenomeInterval.divide(subivl, excl_overlapping)
                    else:
                        yield subivl
            else:
                yield from intersection
