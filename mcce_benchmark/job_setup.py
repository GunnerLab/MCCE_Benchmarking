#!/usr/bin/env python

"""Module: job_setup.py

Contains functions to prepare a user's benchmarking folder using user-provided options
(from cli args if cli is used).

Functions:
----------
* setup_pdbs_folder(benchmarks_dir:str) -> None:
    Replicate current setup.
    - Create a copy of BENCH_PDBS (packaged data) in user_pdbs_folder = `benchmarks_dir`/RUNS,
      or in user_pdbs_folder = `./RUNS` if called from within `benchmarks_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmarks_dir`.

* delete_sentinel(benchmarks_dir:str, sentinel_file:str) -> None:
    Part of the job preparation for each new script.
    Delete sentinel_file from 'benchmarks_dir'/RUNS subfolders.

* write_run_script(job_name, steps_options_dict)
    Beta Phase : job_name = "default_run" (or soft link to 'default_run.sh' if different).
    Write a shell script in user_job_folder similar to RUN_SH_DEFAULTS.

    Current default template: (BENCH.DEFAULT_JOB_SH, "default_run.sh"):
     ```
     #!/bin/bash

     step1.py --dry prot.pdb
     step2.py -d 4
     step3.py -d 4
     step4.py --xts

     sleep 10
     ```
"""

#...............................................................................
from mcce_benchmark import BENCH, RUNS_DIR, MCCE_EPS, N_BATCH, N_PDBS
from mcce_benchmark import audit
from mcce_benchmark.io_utils import Pathok
import logging
import os
from pathlib import Path
import shutil
from typing import Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



def setup_mcce_runs(pdbs_list:str, benchmarks_dir:str) -> None:
    """
    - Create subfolders for the pdbs found in 'pdbs_list', which is a file or dir path,
      in <benchmarks_dir>/RUNS;
    - Soft-link the relevant pdb as "prot.pdb";
    - Create a "queue book" and default script files in <benchmarks_dir>/RUNS;
    """


def setup_expl_runs(benchmarks_dir:str, n_pdbs:int) -> None:
    """
    Replicate current setup.
    - Create a copy of BENCH_PDBS (packaged data) in <benchmarks_dir>/RUNS, or a subset
      of size (1, n_pdbs) if n_pdbs < 120.
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH)
      in <benchmarks_dir>/RUNS;
    """

    benchmarks_dir = Path(benchmarks_dir)
    curr = Path.cwd()
    in_benchmarks = curr.name == benchmarks_dir.name

    if in_benchmarks:
        logger.info(f"Call from within {benchmarks_dir}, not re-created.")
    else:
        if not benchmarks_dir.exists():
            benchmarks_dir.mkdir()

    user_pdbs_folder = benchmarks_dir.joinpath(RUNS_DIR)
    if not user_pdbs_folder.exists():
        user_pdbs_folder.mkdir()

    valid, invalid = audit.list_all_valid_pdbs()
    for i, v in enumerate(valid):
        if i == n_pdbs:
            break

        # v :: PDBID/pdbid.pdb
        p = user_pdbs_folder.joinpath(v)
        d = p.parent
        if not d.is_dir():
            d.mkdir()

        if not p.exists():
            shutil.copy(BENCH.BENCH_PDBS.joinpath(v), p)

        ## also copy full if prot is multi:
        #if p.name.startswith(f"{d.name.lower()}_"):
        #    if not d.joinpath(f"{d.name.lower()}.pdb.full").exists():
        #        try:
        #            shutil.copy(BENCH.BENCH_PDBS.joinpath(f"{d.name}",
        #                                                  f"{d.name.lower()}.pdb.full"),
        #                        d)
        #            logger.info(f"Copied .pdb.full for {d.name}")
        #        except Exception as e:
        #            logger.exception(f".pdb.full not found for {d.name}?", e)
        #            raise

        # cd to avoid links with long names:
        os.chdir(d)
        prot = Path("prot.pdb")
        try:
            prot.symlink_to(p.name)
        except FileExistsError:
            if not prot.is_symlink() or (prot.resolve().name != p.name):
                prot.unlink()
                prot.symlink_to(p.name)
                logger.info(f"Reset soft-linked pdb to prot.pdb for {d.name}")
        os.chdir("../") #d.parent)

    os.chdir(curr)

    # copy script file:
    dest = user_pdbs_folder.joinpath(BENCH.DEFAULT_JOB_SH.name)
    if not dest.exists():
        shutil.copy(BENCH.DEFAULT_JOB_SH, dest)
        logger.info(f"Script file copied: {dest}")

    audit.rewrite_book_file(user_pdbs_folder.joinpath(BENCH.Q_BOOK))
    logger.info(f"The data setup in {user_pdbs_folder} went beautifully!")

    return


def delete_sentinel(benchmarks_dir:str, sentinel_file:str) -> None:
    """Part of the job preparation for each new script.
    Delete sentinel_file from 'benchmarks_dir'/RUNS subfolders.
    """

    benchmarks_dir = Path(benchmarks_dir)
    fl = list(benchmarks_dir.joinpath(RUNS_DIR).glob("./*/"+sentinel_file))
    for f in fl:
        f.unlink()
    logger.info(f"{len(fl)} {sentinel_file!r} file(s) deleted.")

    return


def get_script_contents(sh_path:str):
    with open(sh_path) as f:
        contents = f.read()
    return contents


def get_default_script(pdb_dir:str) -> Path:
    """Re-install BENCH.DEFAULT_JOB_SH in pdb_dir if not found.
    Return its path.
    """

    pdb_dir = Path(pdb_dir)
    sh_path = pdb_dir.joinpath(BENCH.DEFAULT_JOB_SH.name)
    if not sh_path.exists():
        shutil.copy(BENCH.DEFAULT_JOB_SH, sh_path)
        logger.info(f"Re-installed {BENCH.DEFAULT_JOB_SH.name}")

    return sh_path


def write_default_run_script(benchmarks_dir:str,
                             job_name:str = BENCH.DEFAULT_JOB) -> None:
    """
    To use when cli args are all default.
    If job_name is different from "default_run", the default script is soft-linked to it
    as <job_name>.sh
    """

    benchmarks_dir = Path(benchmarks_dir)
    curr = Path.cwd()
    in_benchmarks = curr.name == benchmarks_dir.name
    if in_benchmarks:
        benchmarks_dir = curr

    user_pdbs = Pathok(benchmarks_dir.joinpath(RUNS_DIR))

    # reinstall the default script if not found:
    default_sh = get_default_script(user_pdbs)

    sh_name = f"{job_name}.sh"
    if job_name == BENCH.DEFAULT_JOB:
        sh_path = default_sh
    else:
        # soft-link default_sh to sh_name
        if not in_benchmarks:
            os.chdir(benchmarks_dir)

        os.chdir(user_pdbs)

        sh_path = Path(sh_name)
        try:
            sh_path.symlink_to(BENCH.DEFAULT_JOB_SH.name)
        except FileExistsError:
            sh_path.unlink()
            sh_path.symlink_to(BENCH.DEFAULT_JOB_SH.name)

        logger.info(f"Soft-linked {BENCH.DEFAULT_JOB_SH.name} as {sh_name}")

        # reset path:
        sh_path = user_pdbs.joinpath(sh_name)

    logger.info(f"Script contents:\n{get_script_contents(sh_path)}")
    os.chdir(curr)

    return
