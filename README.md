# IndexTools

Common index formats, such as BAM Index (BAI) and Tabix (TBI), contain coarse-grained information on the density of NGS reads along the genome that may be leveraged for rapid approximation of read depth-based metrics. IndexTools is a toolkit for extremely fast NGS analysis based on index files.

## Installation

### Pre-requisites

* Python 3.6+

### Pip

```bash
pip install indextools
```

### From source

* Clone the repository
  ```
  git clone https://github.com/dnanexus/IndexTools.git
  ```
* You'll need several tools to run the full install and release process
    * [git](https://git-scm.com/)
    * [curl](https://curl.haxx.se/)
    * [make](https://www.gnu.org/software/make/)
    * [Poetry](https://github.com/sdispater/poetry)
    * [Black](https://github.com/python/black)
    * [Flake8](http://flake8.pycqa.org/en/latest/)
    * [Dunamai](https://github.com/mtkennerly/dunamai)
* Then
  ```bash
  # Install locally
  $ make install
  # Release new version (if you are a maintainer)
  $ make release version=<new version> token=<GitHub API Token>
  ```

## Commands

### Partition

The `partition` command processes a BAM index file and generates a file in BED format that contains intervals that are roughly equal in "[volume](#volume)." This partition BAM file can be used for more efficient parallelization of secondary analysis tools (as opposed to parallelizing by chromosome or by uniform windows).

```bash
# Generate a BED with 10 partitions
indextools partition -I tests/data/small.bam.bai \
  -z tests/data/contig_sizes.txt \
  -n 10 \
  -o small.partitions.bed
```

## Limitations

IndexTools is under active development. Please see the [issue tracker](https://github.com/dnanexus/IndexTools/issues) and [road map](https://github.com/dnanexus/IndexTools/projects/1) to view upcoming features.

Some of the most commonly requested features that are not yet available are:

* Support for CRAM files and CRAM indexes (.crai).
* Support for non-local files, via URIs.

## Development

We welcome contributions from the community. Please see the [developer README](https://github.com/dnanexus/IndexTools/blob/develop/CONTRIBUTING.md) for details.

Contributors are required to abide by our [Code of Conduct](https://github.com/dnanexus/IndexTools/blob/develop/CODE_OF_CONDUCT.md).

## Technical details

### Volume

In a bioinformatics context, the term “size” is overloaded. It is used to refer to the linear size of a genomic region (number of bp), disk size (number of bytes), or number of features (e.g. read count). IndexTools estimates the approximate number of bytes required to store the uncompressed data of features within a given genomic region. To avoid confusion or conflation with any of the meanings of “size,” we chose instead to use the term “volume” to refer to the approximate size (in bytes) of a given genomic region. It is almost never important or useful to be able to interpret the meaning of a given volume, nor can volume be meaningfully translated to other units; volume is primarily useful as a relative measure. Thus, we use the made-up unit “V” when referring to any specific volume.

## License

IndexTools is Copyright (c) 2019 DNAnexus, Inc.; and is made available under the [MIT License](https://github.com/dnanexus/IndexTools/blob/develop/LICENSE).

IndexTools is *not* an officially supported DNAnexus product. All bug reports and feature requests should be handled via the [issue tracker](https://github.com/dnanexus/IndexTools/issues). Please *do not* contact DNAnexus support regarding this software.

## Acknowledgements

* The initial inspiration for IndexTools came from @brentp's [indexcov](https://github.com/brentp/goleft/tree/master/indexcov).
* IndexTools is built on several open-source libraries; see the [pyproject.toml](https://github.com/dnanexus/IndexTools/blob/develop/pyproject.toml) file for a full list.
