"""
Module: batch_submit.py

Submit and maintain a big batch of jobs based on book file
State:
 " ": not submitted
 "r": running
 "c": completed - was running, dissapeared from job queue, pK.out generated
 "e": error - was running, dissapeared from job queue and no pK.out
"""

from benchmark import BENCH
import getpass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Union


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


def get_jobs(job_name:str) -> list:
    """
    Query shell for user's processes with job_name.
    Return a list of directories where the jobs are running.
    """

    data = subprocess.run(f"pgrep -u {getpass.getuser()} {job_name}",
                          capture_output=True,
                          text=True,
                          shell=True,
                          )
    if data.returncode:
        # -> in log.Exceptions
        raise subprocess.CalledProcessError(f"Error in subprocess cmd: {data.args}; {data.stderr}; code: {data.returncode}")

    dirs = []
    for uid in data.stdout.splitlines():
        out = subprocess.run(f"pwdx {uid}",
                             capture_output=True,
                             text=True,
                             shell=True
                             )
        if out.returncode:
            #raise subprocess.CalledProcessError(f"Error in subprocess cmd: {out.args}; {out.stderr}; code: {out.returncode}")
            # -> in log.Exceptions
            print(f"Error in subprocess cmd: {out.args}; {out.stderr}; code: {out.returncode}")
            continue

        d = Path(out.stdout.split(":")[1].strip())
        dirs.append(d.name)

    return dirs


def batch_run(job_name:str, n_active:int = BENCH.N_ACTIVE, sentinel_file:str = "pK.out") -> None:
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
    entries = read_book_entries()
    jobs = get_jobs(job_name)
    n_jobs = len(jobs)

    job_script = f"{job_name}.sh"
    if not Path(job_script).exists():
        # -> log
        raise FileNotFoundError(f"The job script ({job_script}) is missing.")

    new_entries = []
    for entry in entries:
        if entry.state == " ":
            n_jobs += 1
            if n_jobs <= n_active:
                os.chdir(entry.name)
                subprocess.Popen(f"../{job_script}", close_fds=True, stdout=open("run.log", "w"))
                os.chdir("../")
                entry.state = "r"
        elif entry.state == "r":
            if entry.name not in jobs:   # was running => completed or error
                entry.state = "e"
                if Path(f"{entry.name}/{sentinel_file}").exists():
                    entry.state = "c"

        new_entries.append(entry)

    newlines = [f"{e}\n" for e in new_entries]
    with open(BENCH.Q_BOOK, "w") as bk:
        bk.writelines(newlines)

    return


def launch_job(benchmarks_dir:Path, job_name:str, n_active:int = N_ACTIVE, sentinel_file:str = "pK.out") -> None:
    """
    Go to benchmarks_dir/clean_pdbs directory & call batch_run.

    Args:
    benchmarks_dir (Path): Path of the folder containing the 'clean_pdbs' folder.
    job_name (str): Name of the job and script to use in 'clean_pdbs' folder.
    n_active (int, BENCH.N_ACTIVE=10): Number of jobs/processes to maintain.
    sentinel_file (str, "pK.out"): File whose existence signals a completed step;
        When running all 4 MCCE steps (default), this file is 'pK.out', while
        when running only the first 2, this file is 'step2_out.pdb'.
    """

    if Path.cwd().name != benchmarks_dir.name:
        os.chdir(benchmarks_dir)

    os.chdir(BENCH.CLEAN_PDBS)
    batch_run(job_name, n_active=n_active, sentinel_file=sentinel_file)
    os.chdir("../")

    return
