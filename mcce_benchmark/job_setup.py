"""Module: job_setup.py

Contains functions to prepare a user's benchmarking folder using user-provided options
(from cli args if cli is used).

Functions:
----------
* setup_pdbs_folder(benchmarks_dir:Path) -> None:
    Replicate current setup.
    - Create a copy of BENCH_PDBS (packaged data) in user_pdbs_folder = `benchmarks_dir/clean_pdbs`,
      or in user_pdbs_folder = `./clean_pdbs` if called from within `benchmarks_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmarks_dir`.

* delete_pkout(benchmarks_dir:Path) -> None:
    Part of the job preparation for each new script.
    Delete pk.out from 'benchmarks_dir/clean_pdbs' subfolders.

* write_run_script(job_name, steps_options_dict)
    Beta Phase : job_name = "default_run" (or soft link to 'default_run.sh' if different).
    Write a shell script in user_job_folder similar to RUN_SH_DEFAULTS.

    Current default template: (BENCH.DEFAULT_JOB_SH):
     ```
     #!/bin/bash
     step1.py --dry prot.pdb
     step2.py -d 4
     step3.py -d 4
     step4.py
     sleep 10
     ```
     Beta Phase: Only the above default script is used; it is soft-linked as job_name.sh if job_name
     is different from "default_run" (i.e the string stored in BENCH.DEFAULT_JOB).
     Future: The script will be name as per args.job_name and its contents will differ depending on the
     options/values passed via the cli.

"""

#...............................................................................
from mcce_benchmark import audit, BENCH, MCCE_EPS, N_SLEEP, N_ACTIVE
import logging
import os
from pathlib import Path
import shutil


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def setup_pdbs_folder(benchmarks_dir:Path) -> None:
    """
    Replicate current setup.
    - Create a copy of BENCH_PDBS (packaged data) in user_pdbs_folder = `benchmarks_dir/clean_pdbs`,
      or in user_pdbs_folder = `./clean_pdbs` if called from within `benchmarks_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmarks_dir`.
    """

    curr = Path.cwd()
    in_benchmarks = curr.name == benchmarks_dir.name

    if in_benchmarks:
        logger.info(f"Call from within {benchmarks_dir}, not re-reated.")
    else:
        if not benchmarks_dir.exists():
            benchmarks_dir.mkdir()

    user_pdbs_folder = benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs_folder.exists():
        user_pdbs_folder.mkdir()
    logger.info(f"{user_pdbs_folder = }")

    valid, invalid = audit.list_all_valid_pdbs()

    for v in valid:
        # v :: PDBID/pdbid.pdb
        p = user_pdbs_folder.joinpath(v)
        d = p.parent
        if not d.is_dir():
            d.mkdir()

        if not p.exists():
            shutil.copy(BENCH.BENCH_PDBS.joinpath(v), p)

        # also copy full if prot is multi:
        if p.name.startswith(f"{d.name.lower()}_"):
            if not d.joinpath(f"{d.name.lower()}.pdb.full").exists():
                try:
                    shutil.copy(BENCH.BENCH_PDBS.joinpath(f"{d.name}",
                                                          f"{d.name.lower()}.pdb.full"),
                                d)
                    logger.info(f"Copied .pdb.full for {d.name}")
                except Exception as e:
                    logger.exception(f".pdb.full not found for {d.name}?", e)
                    raise

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

    # copy ancillary files:
    for i, fp in enumerate([BENCH.DEFAULT_JOB_SH,
                            BENCH.BENCH_Q_BOOK,
                            BENCH.BENCH_WT,
                            BENCH.BENCH_PROTS]):
        if i < 2:
            dest = user_pdbs_folder.joinpath(fp.name)
        else:
            dest = benchmarks_dir.joinpath(fp.name)
        if not dest.exists():
            shutil.copy(fp, dest)
            logger.info(f"Ancillary file: {fp.name} copied to {dest.parent}")

    # include validity check in user's folder:
    logger.info(f"Next: Validity check on user data.")
    valid, invalid = audit.list_all_valid_pdbs(user_pdbs_folder)
    if not invalid:
        logger.info(f"The data setup in {user_pdbs_folder} went beautifully!")

    return


def delete_pkout(benchmarks_dir:Path) -> None:
    """Part of the job preparation for each new script.
    Delete pk.out from 'benchmarks_dir/clean_pdbs' subfolders.
    """

    pkf = list(benchmarks_dir.joinpath(BENCH.CLEAN_PDBS).glob("./*/pK.out"))
    for f in pkf:
        f.unlink()
    logger.info(f"{len(pkf)} pK.out file(s) deleted.")

    return


def get_script_contents(sh_path):
    with open(sh_path) as f:
        contents = f.read()
    return contents


def write_run_script(benchmarks_dir:Path,
                     job_name:str = "default_run") -> None:
    """
    Beta Phase : job_name = "default_run" (or soft link to 'default_run.sh' if different).
    Write a shell script in user_job_folder similar to RUN_SH_DEFAULTS.
    """

    curr = Path.cwd()
    in_benchmarks = curr.name == benchmarks_dir.name
    if in_benchmarks:
        benchmarks_dir = curr

    user_pdbs = benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs.exists():
        msg = f"{benchmarks_dir} does not have a 'clean_pdbs' subfolder: rerun `setup_pdbs_folder` maybe?"
        logger.exception(msg)
        raise FileNotFoundError(msg)

    sh_name = f"{job_name}.sh"
    if job_name == BENCH.DEFAULT_JOB:
        sh_path = user_pdbs.joinpath(sh_name)
        if not sh_path.exists():
            shutil.copy(BENCH.DEFAULT_JOB_SH, sh_path)
            logger.info(f"Re-installed {sh_name}")
    else:
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
