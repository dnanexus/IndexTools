from indextools.console import partition
from pathlib import Path
import filecmp
import pytest

INPUT_DATA_DIR = Path(__file__, "..", "input_data").resolve()
VERIFICATION_DATA_DIR = Path(__file__, "..", "verification_data").resolve()


@pytest.mark.parametrize(
    "index_file,contig_sizes_file,partition_count,expected_partition_bed",
    [
        pytest.param(
            INPUT_DATA_DIR / "small.bam.bai",
            INPUT_DATA_DIR / "contig_sizes.txt",
            10,
            VERIFICATION_DATA_DIR / "small_partitions.bed",
            id="bai_index",
        )
    ],
)
def test_partition_index_w_contigs(
    index_file,
    contig_sizes_file,
    partition_count,
    expected_partition_bed,
    request,
    tmp_path,
):
    """Mimics the following command

    ```
    indextools partition -I <index_file> \
        -z <contig_sizes_file> \
        -n <partition_count> \
        -o <test_name>.partitions.bed
    ```
    """
    partition_bed = tmp_path / "{}.partitions.bed".format(request.node.name)

    partition.partition(
        index=index_file,
        contig_sizes=contig_sizes_file,
        partitions=partition_count,
        outfile=partition_bed,
    )

    assert filecmp.cmp(partition_bed, expected_partition_bed)
