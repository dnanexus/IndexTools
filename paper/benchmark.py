import copy
import json
from pathlib import Path
from typing import Optional
import uuid

import autoclick as ac
import dxpy
import tqdm


@ac.group("benchmark")
def main():
    pass


@main.command()
def launch(
    data_files: Path,
    template: Path,
    workflow_id: str,
    input_stage_id: str = "stage-common",
    output_folder: str = "/benchmark_results",
    summary_file: Path = Path.cwd() / "summary.json",
    batch_id: Optional[str] = None
):
    """
    Launch benchmark analyses.

    Args:
        data_files: JSON file defining the data files on which to benchmark.
        bed_files: JSON file defining the BED files on which to benchmark.
        template: JSON template for static workflow inputs.
        workflow_id: ID of the workflow to execute.
        input_stage_id: ID of the stage that takes the workflow inputs.
        output_folder: Top-level folder in which to output results.
        summary_file: Output summary file to write.
        batch_id: ID to tag on this batch of analyses.
    """
    with open(data_files, "rt") as inp:
        data = json.load(inp)

    with open(template, "rt") as inp:
        tmpl = json.load(inp)

    if batch_id is None:
        batch_id = str(uuid.uuid4())

    workflow = dxpy.DXWorkflow(workflow_id)

    summary = {
        "workflow_id": workflow_id,
        "output_folder": output_folder,
        "batch_id": batch_id,
        "analyses": []
    }

    for data_name, data_val in data.items():
        beds = data_val.pop("beds")
        for bed_name, bed_val in beds.items():
            prefix = f"{data_name}_{bed_name}"
            analysis = copy.copy(tmpl)
            analysis.update(data_val)  # set bam and bai
            analysis["intervals_bed"] = bed_val
            analysis["output_prefix"] = prefix
            summary["analyses"].append(analysis)

        # for each data file we also run a job with no bed file specified -
        # this will cause indextools to be used to generate the bed file
        # from the index
        prefix = f"{data_name}_indextools"
        analysis = copy.copy(tmpl)
        analysis.update(data_val)  # set bam and bai
        analysis["output_prefix"] = prefix
        summary["analyses"].append(analysis)

    for analysis in tqdm.tqdm(summary["analyses"]):
        workflow_inputs = dict(
            (f"{input_stage_id}.{k}", v) for k, v in analysis.items()
        )
        prefix = analysis["output_prefix"]
        folder = f"{output_folder}/{prefix}"
        dxanalysis = workflow.run(
            workflow_inputs,
            folder=folder,
            tags=[batch_id],
            properties={"job_name": prefix}
        )
        analysis["analysis_id"] = dxanalysis.get_id()

    #with open(summary_file, "wt") as out:
    import sys
    json.dump(summary, sys.stdout)


@main.command()
def report(launch_summary: Path, output: Path):
    with open(launch_summary, "rt") as inp:
        summary = json.load(inp)

    results = {}

    for analysis in summary["analyses"]:
        job_name = analysis["output_prefix"]
        dxanalysis = dxpy.DXAnalysis(analysis["analysis_id"])

        # Get the overall runtime

        # Find the GATK job and extract the start and end times from the log

    with open(output, "wt") as out:
        json.dump(results, out)


if __name__ == "__main__":
    main()
