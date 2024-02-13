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

# import class of files resources and constants:
from mcce_benchmark import ENTRY_POINTS, USER, USER_ENV, USER_MCCE
from crontab import CronTab
import logging
from pathlib import Path
import subprocess
import shutil
import sys
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CRON_SH_NAME = "crontab_sh"
CRON_COMMENT = f"Scheduled from {ENTRY_POINTS['launch']}"
#.......................................................................


def subprocess_run(cmd:str,
                   capture_output=True,
                   check:bool=False,
                   text=True,
                   shell=True,
                  ) -> Union[subprocess.CompletedProcess, subprocess.CalledProcessError]:
    """Wraps subprocess.run together with error handling."""

    try:
        data = subprocess.run(cmd,
                              capture_output=capture_output,
                              check=check,
                              text=text,
                              shell=shell
                             )
    except subprocess.CalledProcessError as e:
        #logger.exception(f"Error in subprocess cmd:\nException: {e}")
        #raise
        data = e

    return data


def make_executable(sh_path:Path) -> None:
    """Alternative to os.chmod(sh_path, stat.S_IXUSR): permission denied."""

    cmd = f"chmod +x {sh_path}"

    p = subprocess_run(cmd,
                       capture_output=False,
                       check=True)
    if isinstance(p, subprocess.CalledProcessError):
        logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {p}")
        raise p


def create_cron_sh(benchmarks_dir:Path,
                   job_name:str,
                   n_active:int,
                   sentinel_file:str
                  ) -> Path:
    """
    Create the batch-submitting bash script that crontab will use in
    benchmarks_dir as 'crontab_sh'.
    Return its path
    """

    sh_fstr = """
#!/usr/bin/env sh

#conda run -n <env> <cli> -benchmarks_dir <dir> -job_name <foo> -n_active <n> -sentinel_file <sf>.

conda run -n {} {} -benchmarks_dir {} -job_name {} -n_active {} -sentinel_file {}
"""

    sh_path = benchmarks_dir.joinpath(CRON_SH_NAME)
    with open(sh_path, "w") as fh:
        fh.write(sh_fstr.format(USER_ENV,
                                ENTRY_POINTS["launch"],
                                str(benchmarks_dir),
                                job_name,
                                n_active,
                                sentinel_file))

    make_executable(sh_path)  #needed?
    logger.info(f"Created script for crontab {CRON_SH_NAME!r} in {benchmarks_dir}\n")

    return sh_path



def build_cron_cmd(sh_path:Path) -> str:
    return f"#{CRON_COMMENT}\n* * * * * {str(sh_path)} > $HOME/cron.log 2>&1\n"


def create_crontab(cron_cmd:str, cron_path:str=None) -> None:
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
    """Create a contab entry for batch_submit.py with `launch_args`"""

    sh_path = create_cron_sh(launch_args.benchmarks_dir,
                             launch_args.job_name,
                             launch_args.n_active,
                             launch_args.sentinel_file
                             )
    logger.info("Created the bash script for crontab.")
    cron_cmd = build_cron_cmd(sh_path)
    create_crontab(cron_cmd)
    logger.info("Scheduled batch submission with crontab every minute.")

    return
