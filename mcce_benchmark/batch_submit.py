#!/usr/bin/env python

"""
Module: batch_submit.py

Main functions:
--------------
* read_book_entries(book:str = BENCH.Q_BOOK) -> list:
    Read book file data using ENTRY class.
    Return a list of entry instances.

* get_running_jobs_dirs(job_name:str) -> list:
    Query shell for user's processes with job_name.
    Return a list of RUNS/ sub-directories where the jobs are running.

* batch_run(job_name:str, n_batch:int = N_BATCH, sentinel_file:str = "pK.out") -> None:
    Update Q_BOOK according to user's running jobs' statuses.
    Launch new jobs inside RUNS subfolders until the number of
    job equals n_batch.
    To be run in /RUNS subfolder, which is where Q_BOOK resides.

* launch_job(bench_dir:str),
             job_name:str = None,
             n_batch:int = N_BATCH,
             sentinel_file:str = "pK.out") -> None:
    Go to bench_dir/RUNS directory & call batch_run.

* launch_cli(argv=None)
    Entry point function.


Q book status codes:
     " ": not submitted
     "r": running
     "c": completed - was running, disapeared from job queue, sentinel_file generated
     "e": error - was running, disapeared from job queue and no sentinel_file
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from mcce_benchmark import BENCH, RUNS_DIR, N_BATCH, USER, ENTRY_POINTS
from mcce_benchmark.io_utils import Pathok, subprocess_run
from mcce_benchmark.pkanalysis import pct_completed
import logging
import os
from pathlib import Path
import subprocess
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#.......................................................................


CLI_NAME = ENTRY_POINTS["launch"]  # as per pyproject.toml entry point


class ENTRY:
    def __init__(self):
        self.name = ""
        self.state = " "

    def __str__(self):
        return f"{self.name:6s} {self.state:1s}"


def read_book_entries(book:str = BENCH.Q_BOOK) -> list:
    """Read book file data using ENTRY class.
    Return a list of entry instances.
    """

    entries = []
    with open(book) as bk:
        for line in bk:
            rawtxt = line.strip().split("#")[0]
            fields = rawtxt.split()
            entry = ENTRY()
            entry.name = fields[0]
            if len(fields) > 1:
                entry.state = fields[1].lower()
            entries.append(entry)

    return entries


def get_running_jobs_dirs(job_name:str) -> list:
    """
    Query shell for user's processes with job_name.
    Return a list of RUNS/ sub-directories where the jobs are running.
    """

    # get the process IDs that match job_name from the user's running processes
    data = subprocess_run(f"pgrep -u {USER} {job_name}.sh")
    if data is subprocess.CalledProcessError:
        logger.error("Error with pgrep cmd.")
        raise data

    dirs = []
    for uid in data.stdout.splitlines():
        # get the current working directory of a process
        out = subprocess_run(f"pwdx {uid}")
        if out is subprocess.CalledProcessError:
            logger.error("Error with pwdx cmd.")
            raise out

        d = Path(out.stdout.split(":")[1].strip())
        dirs.append(d.name)

    return dirs


def batch_run(job_name:str, n_batch:int = N_BATCH, sentinel_file:str = "pK.out") -> None:
    """
    Update Q_BOOK according to user's running jobs' statuses.
    Launch new jobs inside the RUNS subfolders until the number of
    job equals n_batch.
    To be run in /RUNS folder, which is where Q_BOOK resides.

    Args:
    job_name (str): Name of the job and script to use in /RUNS folder.
    n_batch (int, BENCH.N_BATCH=10): Number of jobs/processes to maintain.
    sentinel_file (str, "pK.out"): File whose existence signals a completed job;
        When running all 4 MCCE steps (default), this file is 'pK.out', while
        when running only the first 2, this file is 'step2_out.pdb'.
    """

    job_script = f"{job_name}.sh"
    job_script_fp = Pathok(Path(job_script))

    # list of entry instances from Q_BOOK:
    entries = read_book_entries()
    logger.info("Read book entries")
    running_jobs = get_running_jobs_dirs(job_name)
    n_jobs = len(running_jobs)
    logger.info(f"Running jobs: {n_jobs}")

    new_entries = []
    #logger.info("Launching script for unsubmitted entries")
    for entry in entries:
        if entry.state == " ":  # unsubmitted
            n_jobs += 1
            if n_jobs <= n_batch:
                os.chdir(entry.name)
                subprocess.Popen(f"../{job_script}",
                                 shell=True,
                                 close_fds=True,
                                 stdout=open("run.log", "w"))
                os.chdir("../")
                entry.state = "r"
                logger.info(f"Running: {entry.name}")

        elif entry.state == "r":
            if entry.name not in running_jobs:   # was running => completed or error
                entry.state = "e"
                # for debugging:
                sentin_fp = Path(entry.name).joinpath(sentinel_file)
                if sentin_fp.exists():
                    entry.state = "c"
                logger.info(f"Changed {entry.name}: 'r' -> {entry.state!r}")

        new_entries.append(entry)

    # update q-book
    with open(BENCH.Q_BOOK, "w") as bk:
        bk.writelines([f"{e}\n" for e in new_entries])

    return


def launch_job(bench_dir:str,
               job_name:str = BENCH.DEFAULT_JOB,
               n_batch:int = N_BATCH,
               sentinel_file:str = "pK.out") -> None:
    """
    Go to bench_dir/RUNS directory & call batch_run.

    Args:
    bench_dir (Path, None): Path of the folder containing the 'RUNS' folder.
    job_name (str, None): Name of the job and script to use in 'RUNS' folder.
    n_batch (int, BENCH.N_BATCH=10): Number of jobs/processes to maintain.
    sentinel_file (str, "pK.out"): File whose existence signals a completed step;
        When running all 4 MCCE steps (default), this file is 'pK.out', while
        when running only the first 2, this file is 'step2_out.pdb'.
    """

    if bench_dir is None or not bench_dir:
        logger.error("Argument not set: bench_dir.")
        raise ValueError("Argument not set: bench_dir.")

    if job_name is None or not job_name:
        logger.error("Argument not set: job_name.")
        raise ValueError("Argument not set: job_name.")

    bench_dir = Path(bench_dir)
    if Path.cwd().name != bench_dir.name:
        os.chdir(bench_dir)

    os.chdir(RUNS_DIR)

    batch_run(job_name, n_batch=n_batch, sentinel_file=sentinel_file)

    os.chdir("../")

    return



def batch_parser():
    """Command line arguments parser with for batch_submit.launch_job.
    """

    def arg_valid_dirpath(p: str):
        """Return resolved path from the command line."""
        if not len(p):
            return None
        return Path(p).resolve()

    parser = ArgumentParser(
        prog = f"{CLI_NAME} ",
        description = "Same arguments as for mccebench launch_batch.",
        formatter_class = RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-bench_dir",
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking run(s); this is where the
        RUNS folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: mcce_benchmarks.
        """
    )
    parser.add_argument(
        "-job_name",
        type = str,
        default = BENCH.DEFAULT_JOB,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'bench_dir' that launches the MCCE simulation
        in 'bench_dir/RUNS' subfolders; default: %(default)s.
        """
    )
    parser.add_argument(
        "-n_batch",
        type = int,
        default = N_BATCH,
        help = """The number of jobs to keep launching; default: %(default)s.
        """
    )
    parser.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2, this file is 'step2_out.pdb'; default: %(default)s.
        """
    )

    return parser


def launch_cli(argv=None):
    """
    Command line interface for MCCE benchmarking entry point 'mccebench_launchjob'.
    """

    launch_parser = batch_parser()
    args = launch_parser.parse_args(argv)

    if args is None:
        logger.info("Using default args for launch_job")
        launch_job()
    else:
        launch_job(args.bench_dir,
                   args.job_name,
                   args.n_batch,
                   args.sentinel_file)

    book_fp = Path(args.bench_dir).joinpath(BENCH.RUNS_DIR, BENCH.Q_BOOK)
    pct = pct_completed(book_fp)
    logger.info(f"Percentage of jobs completed: {pct:.1%}")

    return


if __name__ == "__main__":

    launch_cli(sys.argv[1:])
