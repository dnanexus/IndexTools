import copy
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Optional, Union
import uuid

import autoclick as ac
import dxpy
from dxpy.utils.job_log_client import DXJobLogStreamClient
import tqdm
from xphyle import STDOUT, open_


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
    batch_id: Optional[str] = None,
    only_data: Optional[str] = None,
    only_bed: Optional[str] = None,
    indextools_only: bool = False
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
        only_data: Name of a data source; only jobs for this source will be launched
        only_bed: Name of a bed file; only jobs for this bed file will be launched
        indextools_only: Only run jobs for indextools
    """
    with open(data_files, "rt") as inp:
        data = json.load(inp)

    if only_data:
        data = {
            only_data: data[only_data]
        }

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
        targets = data_val.pop("targets", None)
        padding = data_val.pop("padding", None)

        if not indextools_only:
            if only_bed:
                beds = {
                    only_bed: beds[only_bed]
                }

            for bed_name, bed_val in beds.items():
                prefix = f"{data_name}_{bed_name}"
                analysis = copy.copy(tmpl)
                analysis.update(data_val)  # set bam and bai
                if targets and isinstance(bed_val, dict):
                    if "bed" in bed_val:
                        analysis["intervals_bed"] = bed_val["bed"]
                    else:
                        analysis["intervals_bed"] = targets
                    analysis["split_column"] = bed_val["split_column"]
                    if padding:
                        analysis["padding"] = padding
                else:
                    analysis["intervals_bed"] = bed_val
                analysis["output_prefix"] = prefix
                summary["analyses"].append(analysis)

        if indextools_only or not only_bed:
            # for each data file we also run a job with no bed file specified -
            # this will cause indextools to be used to generate the bed file
            # from the index
            prefix = f"{data_name}_indextools"
            analysis = copy.copy(tmpl)
            analysis.update(data_val)  # set bam and bai
            if targets:
                analysis["targets_bed"] = targets
                analysis["split_column"] = 4
                if padding:
                    analysis["padding"] = padding
            analysis["output_prefix"] = prefix
            summary["analyses"].append(analysis)

    for analysis in tqdm.tqdm(summary["analyses"]):
        workflow_inputs = dict(
            (f"{input_stage_id}.{k}", v) for k, v in analysis.items()
        )
        prefix = analysis["output_prefix"]
        folder = f"{output_folder}/{prefix}"
        #print(f"Launching workflow with inputs {workflow_inputs}")
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
def report(
    launch_summary: Optional[Path] = None,
    created_after: Optional[str] = None,
    output: Optional[Path] = None
):
    if launch_summary:
        results = summarize_from_launch(launch_summary)
    else:
        if created_after:
            try:
                created_after = int(created_after)
            except:
                pass
        results = summarize_from_query(created_after)

    with open_(output or STDOUT, "wt") as out:
        json.dump(results, out)


def summarize_from_launch(launch_summary: Path):
    with open(launch_summary, "rt") as inp:
        summary = json.load(inp)

    results = {}

    for analysis in summary["analyses"]:
        job_name = analysis["output_prefix"]
        dxanalysis = dxpy.DXAnalysis(analysis["analysis_id"])

        # Get the overall runtime

        # Find the GATK job and extract the start and end times from the log


MSG_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d{6}).*")


class DateCollector:
    def __init__(self):
        self.start = None
        self.end = None

    def __call__(self, msg):
        if msg["source"] == "APP" and msg["level"] == "STDOUT":
            m = MSG_RE.match(msg["msg"])
            if m:
                d = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S,%f")
            if self.start is None:
                self.start = d
            elif self.end is None:
                self.end = d
            else:
                raise RuntimeError("Unexpected date string")

    def duration_seconds(self) -> int:
        return abs(self.start - self.end).seconds


def summarize_from_query(created_after: Optional[Union[int, str]] = None) -> dict:
    summary = {}
    jobs = list(dxpy.find_jobs(
        name="^gatk_hc*",
        name_mode="regexp",
        state="done",
        created_after=created_after,
        project=dxpy.PROJECT_CONTEXT_ID,
        describe=True
    ))
    for job in tqdm.tqdm(jobs):
        job = job["describe"]
        date_collector = DateCollector()
        client = DXJobLogStreamClient(job["id"], msg_callback=date_collector)
        client.connect()
        summary[job["runInput"]["output_prefix"]] = {
            "start": str(date_collector.start),
            "duration": date_collector.duration_seconds()
        }
    return summary


if __name__ == "__main__":
    main()
