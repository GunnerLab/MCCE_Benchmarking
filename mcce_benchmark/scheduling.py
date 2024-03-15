#!/usr/bin/env python

"""
Module: scheduling.py

For automating the crontab creation for scheduling batch_submit every minute.
"""

from argparse import Namespace
from mcce_benchmark import BENCH, ENTRY_POINTS
from mcce_benchmark import USER_MCCE, CONDA_PATH, USER_ENV, N_BATCH
from mcce_benchmark.io_utils import subprocess_run, subprocess
import logging
from pathlib import Path
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#.......................................................................

EP = ENTRY_POINTS["launch"]


def clear_crontab():
    """Remove existing crontab."""

    out = subprocess_run("crontab -r", check=False)
    return


def create_single_crontab(args: Namespace,
                          debug:bool=False) -> Union[None,str]:
    """
    Create a crontab entry without external 'cron.sh script'.
    The user env detected in __init__ is used: the conda env
    is activated in crontab.
    If debug: return crontab_text w/o creating the crontab.
    """

    SINGLE_CRONTAB_fstr = """PATH={}:{}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:
* * * * * {}/conda activate {}; {} -bench_dir {} -job_name {} -n_batch {} -sentinel_file {}"""

    bdir = str(args.bench_dir)
 
    ct_text = SINGLE_CRONTAB_fstr.format(CONDA_PATH,
                                         USER_MCCE,
                                         CONDA_PATH,
                                         USER_ENV,
                                         EP,
                                         bdir,
                                         args.job_name,
                                         args.n_batch,
                                         args.sentinel_file,
                                         )

    crontab_txt = f"{ct_text} > {bdir}/cron_{args.job_name}.log 2>{bdir}/err.log\n"
    logger.info(f"Crontab text:\n```\n{crontab_txt}```")

    if not debug:
        cron_in = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE)
        cur_crontab, _ = cron_in.communicate()
        cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
        cron_out.communicate(input=bytes(crontab_txt, 'utf-8'))

        return

    return crontab_txt


def schedule_job(launch_args:Namespace) -> None:
    """Create a contab entry for batch_submit.py with `launch_args`
    sub-command.
    """

    create_single_crontab(launch_args)
    logger.info("Scheduled batch submission with crontab every minute.")

    return
