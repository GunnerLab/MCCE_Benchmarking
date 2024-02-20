#!/usr/bin/env python

"""
Module: scheduling.py

For automating the crontab creation for scheduling job with the mcce_benchmark dedicated
cli named "mccebench_launchjob"

Implementation:
 1. create bash script to be called by cron
 2. chmod +x
 3. create crontab for that script

"""

from argparse import Namespace as argNamespace
# import class of files resources and constants:
from mcce_benchmark import ENTRY_POINTS, USER, USER_PRFX, USER_ENV, CONDA_PATH
from mcce_benchmark import Pathok
from crontab import CronTab
import logging
from pathlib import Path
import subprocess
import shutil
import sys
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CRON_SH_PREFIX = "crontab"
CRON_COMMENT = f"Scheduled from {ENTRY_POINTS['launch']}"
#.......................................................................


def subprocess_run(cmd:str,
                   capture_output=True,
                   check:bool=False,
                   text=True,
                   shell=True,
                  ) -> Union[subprocess.CompletedProcess, subprocess.CalledProcessError]:
    """Wraps subprocess.run. Return CompletedProcess or err obj."""

    try:
        data = subprocess.run(cmd,
                              capture_output=capture_output,
                              check=check,
                              text=text,
                              shell=shell
                             )
    except subprocess.CalledProcessError as e:
        data = e

    return data


def make_executable(sh_path:str) -> None:
    """Alternative to os.chmod(sh_path, stat.S_IXUSR): permission denied."""

    sh_path = Path(sh_path)
    cmd = f"chmod +x {sh_path}"

    p = subprocess_run(cmd,
                       capture_output=False,
                       check=True)
    if isinstance(p, subprocess.CalledProcessError):
        logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {p}")
        raise p


CONDA_fstr = """
#!/usr/bin/env sh

{} run -n {} {} -benchmarks_dir {} -job_name {} -n_active {} -sentinel_file {}
"""

def create_cron_sh(benchmarks_dir:Path,
                   job_name:str,
                   n_active:int,
                   sentinel_file:str
                  ) -> Path:
    """
    Create the batch-submitting bash script that crontab will use in
    benchmarks_dir as 'crontab_sh'. The main line in the script is:
    '<conda path> run -n <env> <cli> -benchmarks_dir <d> -job_name <jn> -n_active <n> -sentinel_file <sf>'
    Return its path
    """

    cron_sh_name = f"{CRON_SH_PREFIX}_{job_name}_sh"  # no dots!
    sh_path = benchmarks_dir.joinpath(cron_sh_name)
    if sh_path.exists():
        msg = f"A cron script file named {str(sh_path)!r} already exists: Problem.\n"
        msg = msg + "The easiest solution is to choose a different job name.\n"
        msg = msg + "The other one is to acertain that no processes with the same names are running"
        msg = msg + f" using this cmd: 'pgrep -u {USER} {job_name}', so that you can delete the file.\n"
        msg = msg + f"In either cases you need to re-run {ENTRY_POINTS['launch']}."
        logger.error(msg)
        raise FileExistsError(msg)

    with open(sh_path, "w") as fh:
        fh.write(CONDA_fstr.format(CONDA_PATH,
                                   USER_ENV,
                                   ENTRY_POINTS["launch"],
                                   str(benchmarks_dir),
                                   job_name,
                                   n_active,
                                   sentinel_file))

    make_executable(sh_path)  #needed?
    logger.info(f"Created script for crontab {cron_sh_name!r} in {benchmarks_dir}\n")

    return sh_path


def create_crontab(sh_path:str, benchmarks_dir:str, job_name:str, debug:bool=False) -> Union[None,str]:
    """
    Create a crontab entry with'.
    Note: cron_path could hold env variable.
    If debug: return crontab_text w/o creating the crontab.
    """

    cron = CronTab(user=True)
    #NIX?: not necessary now that cron scripts are unique?:
    # Remove all cron jobs with the automated comment
    #cron.remove_all(comment=CRON_COMMENT)

    crontab_txt = f"#{CRON_COMMENT}\n* * * * * {str(sh_path)}"
    crontab_txt = crontab_txt + f" > {benchmarks_dir}/cron_{job_name}.log 2>&1\n"
    logger.info(f"Crontab text:\n{crontab_txt}")

    if not debug:
        cron_in = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE)
        cur_crontab, _ = cron_in.communicate()
        cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
        cron_out.communicate(input=bytes(crontab_txt, 'utf-8'))

    logger.info("User's cron jobs, if any:")
    for job in cron:
        logger.info(f"{job}\n")

    if not debug:
        return
    else:
        return crontab_txt


def create_crontab_old(cron_cmd:str, cron_path:str=None) -> None:
    """
    Create a crontab entry with 'cron_cmd'; precede it with 'cron_path' if not None.
    Note: cron_path could hold env variable.
    """

    cron = CronTab(user=True)
    # Remove all cron jobs with the automated comment
    cron.remove_all(comment=CRON_COMMENT)

    cron_in = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE)
    cur_crontab, _ = cron_in.communicate()

    if cron_path is None:
        crontab_txt = cron_cmd
    else:
        crontab_txt = cron_path + cron_cmd
    crontab_text = crontab_text + " > $HOME/cron.log 2>&1"

    logger.info(f"Crontab text:\n{crontab_txt}")

    cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
    cron_out.communicate(input=bytes(crontab_txt, 'utf-8'))

    logger.info("User's cron jobs, if any:")
    for job in cron:
        logger.info(f"{job}\n")

    return


def schedule_job(launch_args:argNamespace) -> None:
    """Create a contab entry for batch_submit.py with `launch_args`
    sub-command.
    """

    sh_path = create_cron_sh(launch_args.benchmarks_dir,
                             launch_args.job_name,
                             launch_args.n_active,
                             launch_args.sentinel_file
                             )
    logger.info("Created the bash script for crontab.")
    create_crontab(sh_path, launch_args.benchmarks_dir, launch_args.job_name)
    logger.info("Scheduled batch submission with crontab every minute.")

    return
