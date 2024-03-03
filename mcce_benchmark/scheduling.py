#!/usr/bin/env python

"""
Module: scheduling.py

For automating the crontab creation for scheduling batch_submit every minute.
"""

from argparse import Namespace as argNamespace
# import class of files resources and constants:
from mcce_benchmark import USER_MCCE, CONDA_PATH, USER_ENV
from mcce_benchmark import Pathok
import logging
from pathlib import Path
import subprocess
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#.......................................................................

def subprocess_run(cmd:str,
                   capture_output=True,
                   check:bool=False,
                   text=True,
                   shell=True,
                  ) -> Union[subprocess.CompletedProcess,
                             subprocess.CalledProcessError]:
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


#DEPRECATE?
def brc_conda_is_valid() -> bool:
    """Remove existing file if empty.
    Was used to test a SO recipe; see extract_conda_init.
    TEMP."""

    brc_conda = Path("~/.bashrc_conda").expanduser()
    with open(brc_conda) as fh:
        n = len(fh.readlines())
    if n:
        return True
    else:
        brc_conda.unlink()
        return False



#DEPRECATE?
def extract_conda_init(brc_file:str="~/.bashrc"):
    """Extract conda initialization snippet from ~/.bashrc into ~/.bashrc_conda
    SO:
    https://stackoverflow.com/questions/36365801/run-a-crontab-job-using-an-anaconda-env/60977676#60977676
    TEMP.
    """

    brc = Path(brc_file).expanduser()
    brc_conda = Path("~/.bashrc_conda").expanduser()
    if brc_conda.exists() and brc_conda_is_valid():
        #print("brc_conda exists")
        return

    #1. Copy the conda snippet from ~/.bashrc to ~/.bashrc_conda
    cmd = f"sed -n '/# >>> conda initialize/,/# <<< conda initialize/p' {brc} > {brc_conda}"
    result = subprocess_run(cmd,
                            capture_output=False,
                            check=True
                            )

    if isinstance(result, subprocess.CalledProcessError):
        logger.exception(f"Error in subprocess for bashrc_conda:\nException: {result}")
        raise result
    elif isinstance(result, subprocess.CompletedProcess):
        with open(brc_conda) as fh:
            lines = fh.readlines()
        if not lines:
            msg = "~/.bashrc has no conda initalization snippet."
            logger.error(msg)
            raise subprocess.CalledProcessError(1, cmd)

    logger.info("Created ~/.bashrc_conda")
    return

extract_conda_init()


def make_executable(sh_path:str) -> None:
    """Alternative to os.chmod(sh_path, stat.S_IXUSR): permission denied."""

    sh_path = Pathok(sh_path)
    cmd = f"chmod +x {str(sh_path)}"

    p = subprocess_run(cmd,
                       capture_output=False,
                       check=True)
    if isinstance(p, subprocess.CalledProcessError):
        logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {p}")
        raise p


def create_single_crontab(benchmarks_dir:Path,
                          job_name:str,
                          n_active:int,
                          sentinel_file:str,
                          debug:bool=False) -> Union[None,str]:
    """
    Create a crontab entry without external 'cron.sh script'.
    If debug: return crontab_text w/o creating the crontab.
    """

    old_SINGLE_CRONTAB_fstr = """SHELL=/bin/bash
BASH_ENV=~/.bashrc_conda
* * * * * conda activate {}; {} -benchmarks_dir {} -job_name {} -n_active {} -sentinel_file {}"""

    prev_SINGLE_CRONTAB_fstr = """PATH={}:{}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:
* * * * * conda run -n {}; {} -benchmarks_dir {} -job_name {} -n_active {} -sentinel_file {}"""

    # Potential issue: is <job_name>.sh script listed in processes? -> 'mcce'
    SINGLE_CRONTAB_fstr = """PATH={}:{}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:
* * * * * {}/conda run -n {} python -m mcce_benchmark.batch_submit -benchmarks_dir {} -job_name {} -n_active {} -sentinel_file {}"""

    bdir = str(benchmarks_dir)
    ct_text = SINGLE_CRONTAB_fstr.format(CONDA_PATH,
                                         USER_MCCE,
                                         CONDA_PATH,
                                         USER_ENV,
                                         bdir,
                                         job_name,
                                         n_active,
                                         sentinel_file,
                                         )

    crontab_txt = f"{ct_text} > {bdir}/cron_{job_name}.log 2>&1\n"
    logger.info(f"Crontab text:\n```\n{crontab_txt}```")

    if not debug:
        cron_in = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE)
        cur_crontab, _ = cron_in.communicate()
        cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
        cron_out.communicate(input=bytes(crontab_txt, 'utf-8'))

        #logger.info(f"New job to look for in pgrep: {job_name}.sh?")
        return

    return crontab_txt


def schedule_job(launch_args:argNamespace) -> None:
    """Create a contab entry for batch_submit.py with `launch_args`
    sub-command.
    """

    # case with conda run -n env in ctab
    create_single_crontab(launch_args.benchmarks_dir,
                            launch_args.job_name,
                            launch_args.n_active,
                            launch_args.sentinel_file
                            )
    logger.info("Scheduled batch submission with crontab every minute.")

    return
