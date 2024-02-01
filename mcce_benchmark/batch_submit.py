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
    Return a list of clean_pdbs sub-directories where the jobs are running.

* batch_run(job_name:str, n_active:int = N_ACTIVE, sentinel_file:str = "pK.out") -> None:
    Update Q_BOOK according to user's running jobs' statuses.
    Launch new jobs inside clean_pdbs subfolders until the number of
    job equals n_active.
    To be run in /clean_pdbs folder, which is where Q_BOOK resides.

* launch_job(benchmarks_dir:Path = None,
             job_name:str = None,
             n_active:int = N_ACTIVE,
             sentinel_file:str = "pK.out") -> None:
    Go to benchmarks_dir/clean_pdbs directory & call batch_run.

Q book status codes:
     " ": not submitted
     "r": running
     "c": completed - was running, disapeared from job queue, sentinel_file generated
     "e": error - was running, disapeared from job queue and no sentinel_file
"""

from mcce_benchmark import BENCH, N_ACTIVE, USER, DEFAULT_DIR, 
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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


def subprocess_run(cmd:str, do_check:bool=False) -> subprocess.CompletedProcess:
    """Wraps subprocess.run together with error handling."""

    try:
        data = subprocess.run(cmd,
                              capture_output=True,
                              check=do_check,
                              text=True,
                              shell=True,
                             )
    except subprocess.CalledProcessError as e:
        logger.exception(f"Error in subprocess cmd:\nException: {e}")
        raise

    return data


def get_running_jobs_dirs(job_name:str) -> list:
    """
    Query shell for user's processes with job_name.
    Return a list of clean_pdbs sub-directories where the jobs are running.
    """

    # get the process IDs that match job_name from the user's running processes
    data = subprocess_run(f"pgrep -u {USER} {job_name}")
    dirs = []
    for uid in data.stdout.splitlines():
        # get the current working directory of a process
        out = subprocess_run(f"pwdx {uid}")
        d = Path(out.stdout.split(":")[1].strip())
        dirs.append(d.name)

    return dirs



def get_jobs():
    """From legacy.batch_submit.py"""

    lines = subprocess.Popen(["ps", "-u", USER],
                             stdout=subprocess.PIPE).stdout.readlines()
    job_uids = [x.decode("ascii").split()[0] for x in lines if x.decode("ascii").find(job_name) > 0]
    job_uids = [x for x in job_uids if x and x != "PID"]

    jobs = []
    for uid in job_uids:
        output = subprocess.Popen(["pwdx", uid], stdout=subprocess.PIPE).stdout.readlines()[0].decode("ascii")
        job = output.split(":")[1].split("/")[-1].strip()
        if job:
            jobs.append(job)
    return jobs



def batch_run(job_name:str, n_active:int = N_ACTIVE, sentinel_file:str = "pK.out") -> None:
    """
    Update Q_BOOK according to user's running jobs' statuses.
    Launch new jobs inside clean_pdbs subfolders until the number of
    job equals n_active.
    To be run in /clean_pdbs folder, which is where Q_BOOK resides.

    Args:
    job_name (str): Name of the job and script to use in /clean_pdbs folder.
    n_active (int, BENCH.N_ACTIVE=10): Number of jobs/processes to maintain.
    sentinel_file (str, "pK.out"): File whose existence signals a completed job;
        When running all 4 MCCE steps (default), this file is 'pK.out', while
        when running only the first 2, this file is 'step2_out.pdb'.
    """

    job_script = f"{job_name}.sh"
    if not Path(job_script).exists():
        logger.exception(f"The job script ({job_script}) is missing.")
        raise FileNotFoundError(f"The job script ({job_script!r}) is missing.")

    # list of entry instances from Q_BOOK:
    entries = read_book_entries()
    logger.info("Read book entries")
    running_jobs = get_running_jobs_dirs(job_name)
    n_jobs = len(running_jobs)
    logger.info(f"Running jobs: {n_jobs}")

    new_entries = []
    logger.info("Launching script for unsubmitted entries")
    for entry in entries:
        if entry.state == " ":  # unsubmitted
            n_jobs += 1
            if n_jobs <= n_active:
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
                logger.info(f"Sentinel: {sentin_fp}; Exists: {sentin_fp.exists()}")
                # was Path(f"{entry.name}/{sentinel_file}")
                if sentin_fp.exists():
                    entry.state = "c"
                logger.info(f"Changed {entry.name}: 'r' -> {entry.state!r}")

        new_entries.append(entry)

    # update q-book
    with open(BENCH.Q_BOOK, "w") as bk:
        bk.writelines([f"{e}\n" for e in new_entries])

    return

default_path = Path(DEFAULT_DIR)
def launch_job(benchmarks_dir:Path = default_path,
               job_name:str = BENCH.DEFAULT_JOB,
               n_active:int = N_ACTIVE,
               sentinel_file:str = "pK.out") -> None:
    """
    Go to benchmarks_dir/clean_pdbs directory & call batch_run.

    Args:
    benchmarks_dir (Path, None): Path of the folder containing the 'clean_pdbs' folder.
    job_name (str, None): Name of the job and script to use in 'clean_pdbs' folder.
    n_active (int, BENCH.N_ACTIVE=10): Number of jobs/processes to maintain.
    sentinel_file (str, "pK.out"): File whose existence signals a completed step;
        When running all 4 MCCE steps (default), this file is 'pK.out', while
        when running only the first 2, this file is 'step2_out.pdb'.
    """

    if benchmarks_dir is None:
        logger.exception("Argument not set: benchmarks_dir is None.")
        raise ValueError("Argument not set: benchmarks_dir is None.")

    if job_name is None:
        logger.exception("Argument not set: job_name is None.")
        raise ValueError("Argument not set: job_name is None.")

    if Path.cwd().name != benchmarks_dir.name:
        os.chdir(benchmarks_dir)

    os.chdir(BENCH.CLEAN_PDBS)
    batch_run(job_name, n_active=n_active, sentinel_file=sentinel_file)
    os.chdir("../")

    return


if __name__ == "__main__":

    if sys.argv is None:
        launch_job()
    else:
        launch_job(sys.argv)


