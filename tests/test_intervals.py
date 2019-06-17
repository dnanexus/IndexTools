import pickle
from pathlib import Path
import pytest
import random
from typing import Sequence

from indextools.intervals import GenomeInterval, InterLap, Side


DB_INTERVALS_PER_CONTIG = 1000
QUERY_INTERVALS_PER_CONTIG = 100
CONTIG = "chr1"
CONTIG_SIZE = 100000


def random_intervals(
    contig: str, contig_size: int, num_intervals: int
) -> Sequence[GenomeInterval]:
    """
    Generates a random number of intervals for each contig, with random start and end
    positions.
    """
    num_intervals = random.randrange(num_intervals)
    pop = range(contig_size)
    pos = random.sample(pop, 2 * num_intervals)
    return sorted((
        GenomeInterval(contig, *sorted((start, end)))
        for start, end in zip(pos[:num_intervals], pos[num_intervals:])
    ))


@pytest.fixture()
def database_intervals():
    return random_intervals(CONTIG, CONTIG_SIZE, DB_INTERVALS_PER_CONTIG)


@pytest.fixture()
def query_intervals():
    return random_intervals(CONTIG, CONTIG_SIZE, QUERY_INTERVALS_PER_CONTIG)


class FailureCache:
    def __init__(self):
        self.path = Path(".failures")
        self._name = None
        self._objs = None

    def __call__(self, name: str, **objs):
        self._name = name
        self._objs = objs
        return self

    def _cache(self):
        if self._name and self._objs:
            if not self.path.exists():
                self.path.mkdir()
            with open(self.path / self._name, "wb") as out:
                pickle.dump(self._objs, out)

    def _reset(self):
        self._name = None
        self._objs = None

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self._cache()
        self._reset()


@pytest.fixture(scope="session")
def fail_cache():
    return FailureCache()


class TestInterlap:
    def test_closest_left(
        self,
        database_intervals: Sequence[GenomeInterval],
        query_intervals: Sequence[GenomeInterval],
        fail_cache: FailureCache
    ):
        def slow_find_closest(query_ivl: GenomeInterval):
            closest = []
            for i, db_ivl in enumerate(database_intervals):
                if db_ivl.end > query_ivl.start:
                    if i > 0:
                        i -= 1
                        c0 = database_intervals[i]
                        closest.append(c0)
                        while i > 0:
                            i -= 1
                            c = database_intervals[i]
                            if c.end == c0.end:
                                closest.append(c)
                            else:
                                break
                    break

            return closest

        db = InterLap()
        db.add(database_intervals)
        for query in query_intervals:
            actual = list(db.closest(query, Side.LEFT))
            expected = slow_find_closest(query)
            with fail_cache(
                "test_closest_left",
                query=query,
                actual=actual,
                expected=expected,
                db=db
            ):
                assert set(actual) == set(expected)
