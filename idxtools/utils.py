import os
from pathlib import Path
from typing import (
    Dict,
    Generic,
    Iterable,
    Iterator,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import pysam
from xphyle.utils import read_delimited


class FileFormatError(Exception):
    pass


T = TypeVar("T")


class OrderedSet(Generic[T]):
    """Simple set (does not implement the full set API) based on dict that
    maintains addition order.
    """

    def __init__(self, items: Iterable[T] = None) -> None:
        self.items = {}
        if items:
            self.update(items)

    def add(self, item: T) -> None:
        self.items[item] = True

    def update(self, items: Iterable[T]) -> None:
        for item in items:
            self.items[item] = True

    def __iter__(self) -> Iterator[T]:
        return iter(self.items.keys())


class References:
    """Stores map of reference name to size, and provides access to reference_list
    in different formats.
    """

    def __init__(self, references: Sequence[Tuple[str, int]]):
        self.reference_list = list(references)
        self._names = None
        self._lengths = None
        self._id_to_name = None
        self._name_to_size = None

    def __len__(self) -> int:
        return len(self.reference_list)

    def __contains__(self, ref: Union[str, int]):
        if isinstance(ref, int):
            name = self.id_to_name[cast(int, ref)]
        else:
            name = cast(str, ref)
        return name in self.name_to_size

    def __getitem__(self, item: Union[str, int]) -> int:
        return self.get_size(item)

    def __repr__(self) -> str:
        return f"References(" \
            f"{','.join(f'{k}={str(v)}' for k, v in self.name_to_size.items())})"

    def get_size(self, ref: Union[str, int]) -> int:
        """Gets the size of a reference.

        Args:
            ref: A reference name or index.

        Returns:
            The size of the reference.
        """
        if isinstance(ref, int):
            name = self.id_to_name[cast(int, ref)]
        else:
            name = cast(str, ref)
        return self.name_to_size[name]

    @property
    def names(self) -> Sequence[str]:
        """Sequence of reference names.
        """
        if self._names is None:
            self._names = tuple(ref[0] for ref in self.reference_list)
        return self._names

    @property
    def lengths(self) -> Sequence[int]:
        """Sequence of reference lengths.
        """
        if self._lengths is None:
            self._lengths = tuple(ref[1] for ref in self.reference_list)
        return self._lengths

    @property
    def name_to_size(self) -> Dict[str, int]:
        """Mapping of reference name to size.
        """
        if self._name_to_size is None:
            self._name_to_size = dict(self.reference_list)
        return self._name_to_size

    @property
    def id_to_name(self) -> Dict[int, str]:
        """Mapping of reference index to reference name.
        """
        if self._id_to_name is None:
            self._id_to_name = dict(
                (i, ref[0]) for i, ref in enumerate(self.reference_list)
            )
        return self._id_to_name

    @staticmethod
    def from_file(path: Path) -> "References":
        """Loads references from a tsv file with two columns: ref_name, ref_size.

        Args:
            path: The path of the tsv file.

        Returns:
            A References object.
        """
        return References(list(read_delimited(path, converters=[str, int])))

    @staticmethod
    def from_bam(bam: Union[Path, pysam.AlignmentFile]) -> "References":
        """Loads references from the header of a BAM file.

        Args:
            bam: Either a path to a BAM file or an open pysam.AlignmentFile.

        Returns:
            A References object.
        """
        def bam_to_references(_bam):
            return References(list(zip(_bam.references, _bam.lengths)))

        if isinstance(bam, Path):
            with pysam.AlignmentFile(str(bam), "rb") as bam_file:
                return bam_to_references(bam_file)
        else:
            return bam_to_references(bam)


def split_path(path: Path) -> Tuple[Path, str, Sequence[str]]:
    """
    Splits a path into parts.

    Args:
        path: The path to split

    Returns:
        Tuple of (basename, prefix, exts), where exts is a sequence of filename
        extensions.
    """
    name = path.name
    prefix, suffix = name.split(os.extsep, 1)
    return path.parent, prefix, suffix.split(os.extsep)


def replace_suffix(path: Path, new_suffix: str) -> Path:
    """
    Replace the current suffix of `path` (everything from the first '.' on) with
    `new_suffix`.

    Args:
        path:
        new_suffix:

    Returns:

    """
    parts = split_path(path)
    return parts[0] / (parts[1] + new_suffix)
