from indextools.console import partition
import filecmp
import pytest


@pytest.mark.parametrize(
    "index_file,contig_sizes_file,partition_count,expected_partition_bed",
    [
        pytest.param(
            "small.bam.bai",
            "contig_sizes.txt",
            10,
            "small_partitions.bed",
            id="bai_index",
        )
    ],
)
def test_partition_index_w_contigs(
    index_file,
    contig_sizes_file,
    partition_count,
    expected_partition_bed,
    datapath,
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
    # Arrange input datafiles
    index_file = datapath[index_file]
    contig_sizes_file = datapath[contig_sizes_file]
    expected_partition_bed = datapath[expected_partition_bed]

    partition_bed = tmp_path / "{}.partitions.bed".format(request.node.name)

    partition.partition(
        index=index_file,
        contig_sizes=contig_sizes_file,
        partitions=partition_count,
        outfile=partition_bed,
    )

    assert filecmp.cmp(partition_bed, expected_partition_bed)
