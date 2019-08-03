## Prerequisites

* Docker
* Java 1.8+
* Cromwell (for local testing)
* dxWDL (for running on DNAnexus)

## Setup

1. Build the GATK Docker image:
    ```
    cd gatk \
    && export HTS_VERSION=1.9 \
    && export GATK_VERSION=4.1.2.0 \
    && docker build \
      --build-arg HTS_VERSION=$HTS_VERSION \
      --build-arg GATK_VERSION=$GATK_VERSION \
      -t indextools/gatk:gatk-$GATK_VERSION-hts-$HTS_VERSION .
    ```
2. If running on DNAnexus:
    * Push the GATK Docker image to a repository such as DockerHub or Quay.
    * Compile the GATK workflow using dxWDL

## Running the tests

