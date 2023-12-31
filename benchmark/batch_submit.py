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
        # -> in log
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
            # -> in log
            print(f"Error in subprocess cmd: {out.args}; {out.stderr}; code: {out.returncode}")
            continue

        d = Path(out.stdout.split(":")[1].strip())
        dirs.append(d.name)

    return dirs


def batch_run(job_name:str, n_active:int = BENCH.N_ACTIVE) -> None:
    """
    Update Q_BOOK according to user's running jobs' statuses.
    Launch new jobs inside clean_pdbs subfolders until the number of
    job equals n_active.
    To be run where Q_BOOK resides.
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
                if Path(f"{entry.name}/pK.out").exists():
                    entry.state = "c"

        new_entries.append(entry)

    newlines = [f"{e}\n" for e in new_entries]
    with open(Q_BOOK, "w") as bk:
        bk.writelines(newlines)

    return


def launch_job(user_job_folder:Path, job_name, n_active:int = N_ACTIVE) -> None:
    """
    Go to user_job_folder/clean_pdbs directory, call batch_run.
    New batch_submit.main().
    """

    if Path.cwd().name != user_job_folder.name:
        os.chdir(user_job_folder)

    os.chdir("clean_pdbs")
    batch_run(job_name, n_active)

    return
