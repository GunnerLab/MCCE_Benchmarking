#!/usr/bin/env python

"""
Module: scheduling.py

For automating the crontab creation for scheduling batch_submit every minute.
"""

from argparse import Namespace as argNamespace
from mcce_benchmark import ENTRY_POINTS, USER_MCCE, CONDA_PATH, USER_ENV
import logging
from pathlib import Path
import subprocess
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#.......................................................................

EP = ENTRY_POINTS["launch"]

def create_single_crontab(bench_dir:Path,
                          job_name:str,
                          n_batch:int,
                          sentinel_file:str,
                          debug:bool=False) -> Union[None,str]:
    """
    Create a crontab entry without external 'cron.sh script'.
    If debug: return crontab_text w/o creating the crontab.
    """

    SINGLE_CRONTAB_fstr = """PATH={}:{}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:
* * * * * {}/conda activate {}; {} -bench_dir {} -job_name {} -n_batch {} -sentinel_file {}"""

    bdir = str(bench_dir)
    ct_text = SINGLE_CRONTAB_fstr.format(CONDA_PATH,
                                         USER_MCCE,
                                         CONDA_PATH,
                                         USER_ENV,
                                         EP,
                                         bdir,
                                         job_name,
                                         n_batch,
                                         sentinel_file,
                                         )

    crontab_txt = f"{ct_text} > {bdir}/cron_{job_name}.log 2>&1\n"
    logger.info(f"Crontab text:\n```\n{crontab_txt}```")

    if not debug:
        cron_in = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE)
        cur_crontab, _ = cron_in.communicate()
        cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
        cron_out.communicate(input=bytes(crontab_txt, 'utf-8'))

        return

    return crontab_txt


def schedule_job(launch_args:argNamespace) -> None:
    """Create a contab entry for batch_submit.py with `launch_args`
    sub-command.
    """
    # TODO: change launch_args (from SUB1 or SUB2) to dict so that
    #       --launch in cli.py can be used: if --launch then
    #       dict["n_batch"] = default; dict["sentinel_file"] = default
    
    # case with conda run -n env in ctab
    create_single_crontab(launch_args.bench_dir,
                          launch_args.job_name,
                          launch_args.n_batch,
                          launch_args.sentinel_file
                          )
    logger.info("Scheduled batch submission with crontab every minute.")

    return
