"""
Test suite for benchmarks. Requires pytest and pytest-benchmark.
"""
import pytest
import random
from typing import Sequence, Tuple

from . import GenomeInterval, BasicGenomeInterval
from .cgranges import CgrangesIntervals
from .interlap import InterLapIntervals
# from .ncls import NclsIntervals
# from .pyranges import PyrangesIntervals
from .quicksect import QuicksectIntervals


NUM_CONTIGS = 20
MAX_DB_INTERVALS_PER_CONTIG = 1000
MAX_QUERY_INTERVALS_PER_CONTIG = 100
MIN_CHROM_SIZE = 1000000
MAX_CHROM_SIZE = 100000000
LIBS = {
    "cgranges": CgrangesIntervals,
    "interlap": InterLapIntervals,
    # "ncls": NclsIntervals,
    # "pyranges": PyrangesIntervals,
    "quicksect": QuicksectIntervals,
}


@pytest.fixture(scope="session")
def contigs() -> Sequence[Tuple[str, int]]:
    return [
        (f"chr{i}", random.randrange(MIN_CHROM_SIZE, MAX_CHROM_SIZE))
        for i in range(NUM_CONTIGS)
    ]


def random_intervals(
    contigs: Sequence[Tuple[str, int]], max_intervals_per_contig: int
) -> Sequence[GenomeInterval]:
    """
    Generates a random number of intervals for each contig, with random start and end
    positions.
    """
    intervals = []
    for contig, size in contigs:
        num_intervals = random.randrange(max_intervals_per_contig)
        pop = range(size)
        pos = random.sample(pop, 2 * num_intervals)
        intervals.extend((
            BasicGenomeInterval(contig, *sorted((start, end)))
            for start, end in zip(pos[:num_intervals], pos[num_intervals:])
        ))
    return intervals


@pytest.fixture()
def database_intervals(contigs: Sequence[Tuple[str, int]]):
    return random_intervals(contigs, MAX_DB_INTERVALS_PER_CONTIG)


@pytest.fixture()
def query_intervals(contigs: Sequence[Tuple[str, int]]):
    return random_intervals(contigs, MAX_QUERY_INTERVALS_PER_CONTIG)


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.benchmark(group="update")
def test_update(benchmark, database_intervals, lib: str):
    @benchmark
    def update():
        db = LIBS[lib]()
        db.update(database_intervals)


@pytest.mark.parametrize("lib", LIBS)
@pytest.mark.benchmark(group="find")
def test_find(benchmark, database_intervals, query_intervals, lib: str):
    db = LIBS[lib]()
    db.update(database_intervals)

    @benchmark
    def find():
        return [db.find(ivl) for ivl in query_intervals]


def test_find_equal(database_intervals, query_intervals):
    names = []
    results = []

    for name, lib in LIBS.items():
        names.append(name)
        db = lib()
        db.update(database_intervals)
        results.append([set(db.find(ivl)) for ivl in query_intervals])

    for i in range(1, len(results)):
        print(names[0], names[i])
        assert results[0] == results[i]
        # for j, (a, b) in enumerate(zip(results[0], results[i])):
        #     try:
        #         assert a == b
        #     except:
        #         print(query_intervals[j], a, b)
        #         raise
