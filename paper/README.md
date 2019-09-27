## Prerequisites

* Docker
* Java 1.8+
* Cromwell (for local testing)
* dxWDL v1.30+ (for running on DNAnexus)

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
    * Ensure the Docker image is stored as a file on the platform
    * Compile the GATK workflow using dxWDL:
    
        ```commandline
        $ java -jar $DXWDL_JAR compile gatk_benchmark.wdl \
          -project $DXWDL_PROJECT \
          -folder /Benchmark/Workflow \
          -inputs inputs.json \
          -f
        ```

## Running the tests

First ensure you have python 3.6+ installed and install the dependencies:

```commandline
$ pip install -r requirements.txt
```

To launch the benchmarking jobs on DNAnexus, ensure you are logged in and have selected the project where you want to run the analyses. Then run:

```commandline
$ python benchmark.py \
  --data-files data_files.json \
  --bed-files bed_files.json \
  --template inputs.dx.template.json \
  --workflow-id <workflow_id from output of dxWDL compile>
```

A progress bar is displayed, and at the end a summary.json file is written. This file contains all the details on the jobs that were launched.

You can check the status of the jobs by running:

```commandline
$ python benchmark.py status summary.json
```

When the jobs have finished running successfully, you can generate the report:

```commandline
$ python benchmark.py report summary.json

