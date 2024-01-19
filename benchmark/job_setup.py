"""Module: job_setup.py

Contains functions to prepare a user's benchmarking folder using user-provided options
(from cli args if cli is used).

* setup_pdbs_folder(benchmarks_dir:Path) -> Path:
    ```
    Replicate current setup.
    - Create a copy of BENCH_PDBS (pakaged data) in user_pdbs_folder = `benchmarks_dir/clean_pdbs`,
      or in user_pdbs_folder = `./clean_pdbs` if called from within `benchmarks_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmarks_dir`.
    Return the last known path (temporaryly for error checking).
    ```

* write_run_script(job_name, steps_options_dict)
 Write a shell script in user_job_folder similar to RUN_SRC (default template):
 ```
 #!/bin/bash
 step1.py --dry prot.pdb
 step2.py -d 4
 step3.py -d 4
 step4.py
 sleep 10
 ```
 The script will be name as per args.job_name and its contents will differ depending on the chosen
 sub-command and associated options.
 NOTE: The other sub-command, "start_from_step3" is to be implemented after testing of the default one.

* launch_job(q_book, job_name, n_active:int = N_ACTIVE):
 cd user_job_folder/clean_pdbs
 call batch_submit.batch_run(q_book, job_name, n_active:int = N_ACTIVE)
  - q_book is the 'book.txt' file in user_job_folder.
  - batch_submit.batch_run was batch_submit.main()

* implement function for a fresh run in existing folder as per original instructions from jmao:
```
4. Start a fresh batch run
    * make prot.pdb ready  :: part of job_setup step
    * remove pK.out        "" done
    * make book file ready (clear the status code)
    * prepare job script - run.sh
    * edit 3 entries in bin/batch_submit.py
        n_active = 10   # keep this number of active jobs
        queue_book = "book.txt"
        job_name = "run.sh"
    * go to clean_pdbs directory, run ../bin/batch_submit.py :: done in batch_submit.launch_job
    * test if book.txt file has a new time stamp every time you run the batch_submit.py script.
```
"""


#...............................................................................
from benchmark import audit
# import class of files resources and constants:
from benchmark import APP_NAME, BENCH, MCCE_EPS, N_SLEEP, N_ACTIVE, MCCE_OUTPUTS
import getpass
import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Union


mdl_logger = logging.getLogger(f"{APP_NAME}.{__name__}")


#...............................................................................
# This may be used as a template;
# as is, this script is part of the 'clean_pdbs' folder setup: "default_run.sh"
RUN_SH_DEFAULTS = f"""
#!/bin/bash
step1.py --dry prot.pdb
step2.py -d {MCCE_EPS}
step3.py -d {MCCE_EPS}
step4.py

sleep {N_SLEEP}
"""
#.................................................................


# To use for testing submit_script without running anything:

# To check script is run inside a PDB folder:
RUN_SH_TEST_ECHO = f"""
#!/bin/bash

echo "Using RUN_SH_TEST_ECHO as script: $PWD"
"""
# To test mcce can run:
RUN_SH_NORUN = f"""
#!/bin/bash

step1.py prot.pdb --norun
"""
#.................................................................


def setup_pdbs_folder(benchmarks_dir:Path) -> Path:
    """
    Replicate current setup.
    - Create a copy of BENCH_PDBS (packaged data) in user_pdbs_folder = `benchmarks_dir/clean_pdbs`,
      or in user_pdbs_folder = `./clean_pdbs` if called from within `benchmarks_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmarks_dir`.
    Return the last known path (temporarily for error checking).
    """

    curr = Path.cwd()
    if curr.name == benchmarks_dir.name:
        mdl_logger.info("Function 'setup_pdbs_folder' called from within benchmarks_dir, not re-reated.")
        benchmarks_dir = curr
    else:
        if not benchmarks_dir.exists():
            benchmarks_dir.mkdir()

    user_pdbs_folder = benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs_folder.exists():
        user_pdbs_folder.mkdir()

    valid, invalid = audit.list_all_valid_pdbs()
    for v in valid:
        # v :: PDBID/pdbid.pdb
        p = user_pdbs_folder.joinpath(v)
        d = p.parent
        if not d.exists():
            d.mkdir()

        src = BENCH.BENCH_PDBS.joinpath(v)
        if not p.exists():
            shutil.copy(src, p)

        # also copy full if prot is multi:
        if p.name.startswith(f"{p.parent.name.lower()}_"):
            try:
                shutil.copy(BENCH.BENCH_PDBS.joinpath(f"{p.parent.name}",
                                                      f"{p.parent.name.lower()}.pdb.full"),
                            d)
            except Exception as e:
                mdl_logger.exception(f".pdb.full not found for {d.name}?", e)
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
        os.chdir(d.parent)

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
            mdl_logger.info(f"Ancillary file: {fp.name} copied to {dest.parent}")

    # include validity check in user's folder:
    valid, invalid = audit.list_all_valid_pdbs(user_pdbs_folder)
    if len(invalid):
        mdl_logger.error(f"Found {len(invalid)} invalid folder(s):\n{invalid}")
    else:
        mdl_logger.info(f"The data setup in {benchmarks_dir} went beautifully!")

    return Path.cwd()


def change_dir(from_dir:Path, target_dir:Path) -> None:
    if target_dir.name != from_dir.name:
        os.chdir(target_dir)
    return


def delete_pkout(benchmarks_dir:Path) -> None:
    """New job preparation: delete pk.out from 'benchmarks_dir/clen_pdbs' subfolders."""

    for f in benchmarks_dir.joinpath(BENCH.CLEAN_PDBS).glob("./*/pK.out"):
        f.unlink()
    return


def write_run_script(benchmarks_dir:Path,
                     job_name:str = "default_run") -> Path:
    """
    Phase 1: job_name = "default_run" (or soft link to 'default_run.sh' if different).
    Write a shell script in user_job_folder similar to RUN_SH_DEFAULTS.
    Return the script filepath.
    """

    curr = Path.cwd()
    in_benchmarks = curr.name == benchmarks_dir.name
    if in_benchmarks:
        benchmarks_dir = curr

    user_pdbs = benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs.exists():
        msg = f"{benchmarks_dir} does not have a 'clean_pdbs' subfolder: rerun `setup_pdbs_folder` maybe?"
        mdl_logger.exception(msg)
        raise FileNotFoundError(msg)

    if job_name == "default_run":
        sh_path = user_pdbs.joinpath(BENCH.DEFAULT_JOB_SH.name)
        if not sh_path.exists():
            shutil.copy(BENCH.DEFAULT_JOB_SH, sh_path)
    else:
        if not in_benchmarks:
            os.chdir(benchmarks_dir)

        os.chdir(user_pdbs)
        sh_name = f"{job_name}.sh"
        sh_path = Path(sh_name)
        try:
            sh_path.symlink_to(BENCH.DEFAULT_JOB_SH.name)
        except FileExistsError:
            sh_path.unlink()
            sh_path.symlink_to(BENCH.DEFAULT_JOB_SH.name)

        # reset path:
        sh_path = user_pdbs.joinpath(sh_name)

    os.chdir(curr)

    return sh_path


from enum import Enum

# may not need DEFAULT:
class ScriptChoices(Enum):
    TEST_ECHO = RUN_SH_TEST_ECHO
    NORUN = RUN_SH_NORUN
    DEFAULT = RUN_SH_DEFAULTS


def write_run_script_from_template(benchmarks_dir:Path,
                                   job_name:str = "default_run",
                                   script_template:ScriptChoices = None) -> Path:
    """
    Write a shell script in user_job_folder similar to RUN_SH_DEFAULTS.
    Return the script filepath.

    For testing: job_name = "default_run" or script created from template.
    Note: job_name has precedence over script_template: if "default_run" (default), the
    file "default_run.sh" will be copied from the packaged data if it does not exist. Thus,
    the job_name cannot be 'default_run' if script_template is provided.
    """

    user_pdbs = benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs.exists():
        msg = f"{benchmarks_dir} does not have a 'clean_pdbs' subfolder: rerun `setup_pdbs_folder` maybe?"
        mdl_logger.exception(msg)
        raise FileNotFoundError(msg)

    if job_name == "default_run" and script_template is not None:
        print(f"""INFO: 'job_name' has precedence: if "default_run" (default), the file
        'default_run.sh' will be copied from the packaged data if it does not exist.""")

    if job_name == "default_run":
        sh_path = user_pdbs.joinpath(BENCH.DEFAULT_JOB_SH.name)
        if not sh_path.exists():
            shutil.copy(BENCH.DEFAULT_JOB_SH, sh_path)
    else:
        if job_name and script_template is not None:
            sh_path = user_pdbs.joinpath(f"{job_name}.sh")
            if not sh_path.exists():
                with open(sh_path , "w") as fh:
                    fh.write(script_template.value)

                # make script executable:
                #permission denied with os.chmod(sh_path, stat.S_IXUSR)
                try:
                    p = subprocess.run(f"chmod +x {sh_path}",
                                       capture_output=False,
                                       check=True,
                                       shell=True,
                                       )
                except subprocess.CalledProcessError as e:
                    mdl_logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {e}")
                    raise
        else:
            msg = "Missing 'job_name' or no 'script_template' was provided."
            mdl_logger.exception(msg)
            raise ValueError(msg)

    return sh_path
