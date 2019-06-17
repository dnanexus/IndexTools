from abc import ABCMeta, abstractmethod
from typing import Iterable


class GenomeInterval(metaclass=ABCMeta):
    @property
    @abstractmethod
    def contig(self) -> str:
        pass

    @property
    @abstractmethod
    def start(self) -> int:
        pass

    @property
    @abstractmethod
    def end(self) -> int:
        pass

    def __hash__(self) -> int:
        return hash((self.contig, self.start, self.end))

    def __eq__(self, other) -> bool:
        return (
            self.contig == other.contig and
            self.start == other.start and
            self.end == other.end
        )


class BasicGenomeInterval(GenomeInterval):
    __slots__ = ["_contig", "_start", "_end"]

    def __init__(self, contig: str, start: int, end: int):
        self._contig = contig
        self._start = start
        self._end = end

    @property
    def contig(self) -> str:
        return self._contig

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    def __repr__(self):
        return f"{self.contig}:{self.start}-{self.end}"


class Intervals(metaclass=ABCMeta):
    @abstractmethod
    def update(self, intervals: Iterable[GenomeInterval]):
        """
        Add intervals to this object.
        """

    @abstractmethod
    def find(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        """
        Finds all the intervals that overlap `ivl`.
        """

    @abstractmethod
    def nearest_after(self, ivl: GenomeInterval) -> Iterable[GenomeInterval]:
        """
        Finds the nearest interval(s) after (to the right of) `ivl`.
        """
