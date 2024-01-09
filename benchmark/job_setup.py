"""Module: job_setup.py

Contains functions to prepare a user's benchmarking folder using user-provided options
(from cli args if cli is used).

* setup_pdbs_folder(benchmark_dir:Path) -> Path:
    ```
    Replicate current setup.
    - Create a copy of BENCH_PDBS (pakaged data) in user_pdbs_folder = `benchmark_dir/clean_pdbs`,
      or in user_pdbs_folder = `./clean_pdbs` if called from within `benchmark_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmark_dir`.
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
    * make prot.pdb ready
    * remove pK.out
    * make book file ready (clear the status code)
    * prepare job script - run.sh
    * edit 3 entries in bin/batch_submit.py
        n_active = 10   # keep this number of active jobs
        queue_book = "book.txt"
        job_name = "run.sh"
    * go to clean_pdbs directory, run ../bin/batch_submit.py
    * test if book.txt file has a new time stamp every time you run the batch_submit.py script.
```
"""

from benchmark import audit
# import class of files resources and constants:
from benchmark import BENCH, MCCE_EPS, N_SLEEP, N_ACTIVE, MCCE_OUTPUTS
import getpass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Union
#.........................................................................................

RUN_SH_DEFAULTS = f"""
#!/bin/bash
step1.py --dry prot.pdb
step2.py -d {MCCE_EPS}
step3.py -d {MCCE_EPS}
step4.py

sleep {N_SLEEP}
"""

RUN_SH_TEST_ECHO = f"""
#!/bin/bash

echo "Using RUN_SH_TEST_ECHO as script: $PWD"
"""

# template
RUN_SH_TPL = """
#!/bin/bash
step1.py --dry prot.pdb {s1_dict}
step2.py {s2_dict}
step3.py {s3_dict}
step4.py {s4_dict}

sleep {N_SLEEP}
"""


def setup_pdbs_folder(benchmark_dir:Path) -> Path:
    """
    Replicate current setup.
    - Create a copy of BENCH_PDBS (pakaged data) in user_pdbs_folder = `benchmark_dir/clean_pdbs`,
      or in user_pdbs_folder = `./clean_pdbs` if called from within `benchmark_dir`;
    - Soft-link the relevant pdb as "prot.pdb";
    - Copy the "queue book" and default script files (BENCH.BENCH_Q_BOOK, BENCH.DEFAULT_JOB_SH, respectively)
      in `user_pdbs_folder`;
    - Copy ancillary files BENCH.BENCH_WT, BENCH.BENCH_PROTS `benchmark_dir`.
    Return the last known path (temporaryly for error checking).
    """

    curr = Path.cwd()
    if curr.name == benchmark_dir.name:
        #print("fn called from within benchmark_dir, not re-reated.")
        benchmark_dir = curr
    else:
        if not benchmark_dir.exists():
            benchmark_dir.mkdir()

    user_pdbs_folder = benchmark_dir.joinpath(BENCH.CLEAN_PDBS)
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
        #else:
        #    print(f"Not replaced: {p}")

        # also copy full if prot is multi:
        if p.name.startswith(f"{p.parent.name.lower()}_"):
            try:
                shutil.copy(BENCH.BENCH_PDBS.joinpath(f"{p.parent.name}",
                                                      f"{p.parent.name.lower()}.pdb.full"),
                            d)
            except Exception as exc:
                print(f".pdb.full not found for {d.name}?", exc)

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
    for i, fp in enumerate([BENCH.DEFAULT_JOB_SH, BENCH.BENCH_Q_BOOK, BENCH.BENCH_WT, BENCH.BENCH_PROTS]):
        if i < 2:
            dest = user_pdbs_folder.joinpath(fp.name)
        else:
            dest = benchmark_dir.joinpath(fp.name)
        if not dest.exists():
            shutil.copy(fp, dest)
            print(f"Ancillary file: {fp.name} copied to {dest.parent}")

    # include validity check in user's folder:
    valid, invalid = audit.list_all_valid_pdbs(user_pdbs_folder)
    if len(invalid):
        # -> log
        print(f"Setup not right for {len(invalid)} folder(s):\n{invalid}")
    else:
        print(f"The data setup in {benchmark_dir} went beautifully!")

    return Path.cwd()


def reset_curr_dir(from_dir:Path, target_dir:Path) -> None:
    if target_dir.name != from_dir.name:
        os.chdir(target_dir)
    return


def write_run_script(benchmark_dir:Path,
                     job_name:str = "default_run",
                     steps_options_dict:dict = None,
                     sh_template:str = None) -> Path:
    """Phase 1: job_name = "default_run" (or reset to that) => script = "default_run.sh".
    Write a shell script in user_job_folder similar to RUN_SH_DEFAULTS.
    Return the script filepath.
    """
    if job_name != "default_run":
        job_name = "default_run"

    user_pdbs = benchmark_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs.exists():
        raise FileNotFoundError(f"{benchmark_dir} does not have a 'clean_pdbs' subfolder: rerun `setup_pdbs_folder` maybe?")

    sh_path = user_pdbs.joinpath(BENCH.DEFAULT_JOB_SH.name)
    if not sh_path.exists():
        shutil.copy(BENCH.DEFAULT_JOB_SH, sh_path)

    return sh_path
