#!/usr/bin/env python

"""
Module: scheduling.py

For automating the crontab creation for scheduling job with the mcce_bench sub command "mccebench_launchjob"
"""

# import class of files resources and constants:
from mcce_benchmark import ENTRY_POINTS, CRON_COMMENT, USER
from crontab import CronTab
import logging
from pathlib import Path
import subprocess
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#.......................................................................


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
        #logger.exception(f"Error in subprocess cmd:\nException: {e}")
        #raise
        data = None

    return data


def build_cron_path():
    """Replicate PATH as per jmao:
    PATH=/home/jmao/miniconda3/bin: \
    /home/jmao/Stable-MCCE/bin: \
    /home/jmao/bin: \
    /home/jmao/miniconda3/condabin: \
    /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin
    """

    conda_exec = f"/home/{USER}/miniconda3/bin"
    py_exec = Path(sys.executable).parent
    py_exec_str = str(py_exec)
    p = f"#{CRON_COMMENT}\nPATH={conda_exec}:{py_exec_str}:"

    # mcce
    out = subprocess_run('which mcce')
    mcce_str = str(Path(out.stdout.strip()).parent)
    if mcce_str != py_exec_str:
        p = p + f"{mcce_str}:"

    p = p + "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin\n"

    return p


def build_cron_cmd(benchmarks_dir:Path,
                   job_name:str,
                   n_active:int,
                   sentinel_file:str):
    """replicate jmao:
    * * * * * cd /home/jmao/benchmark/e08_calc && /home/jmao/benchmark/bin/batch_submit.py > /tmp/cron.log 2>&1

    mccebench_launchjob -job_name "foo" -n_active 4 -sentinel_file "step2_out.pdb"
    """

    # mccebench_launchjob
    out = subprocess_run(f"which {ENTRY_POINTS['child']}")
    launch_subcmd = str(Path(out.stdout.strip()))

    launch_cmd = f"#{CRON_COMMENT}\n* * * * * cd {str(benchmarks_dir)} && "
    launch_cmd = launch_cmd + f"{launch_subcmd} "
    launch_cmd = launch_cmd + f"-benchmarks_dir {benchmarks_dir} -job_name {job_name} "
    launch_cmd = launch_cmd + f"-n_active {n_active} -sentinel_file {sentinel_file}"
    #launch_cmd = launch_cmd + " > /tmp/cron.log 2>&1\n"
    launch_cmd = launch_cmd + "\n"

    return launch_cmd


def create_crontab(cron_path:str, cron_cmd:str):

    cron = CronTab(user=True)
    # Remove all cron jobs with the automated comment
    cron.remove_all(comment=CRON_COMMENT)

    cron_in = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE)
    cur_crontab, _ = cron_in.communicate()

    logger.info(f"Crontab text:\n{cron_path + cron_cmd}")
    new_crontab = bytes(cron_path + cron_cmd, 'utf-8')
    cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
    cron_out.communicate(input=new_crontab)

    logger.info("User's cron jobs, if any:")
    for job in cron:
        logger.info(f"{job}\n")

    return