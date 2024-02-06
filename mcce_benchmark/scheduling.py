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
from mcce_benchmark import ENTRY_POINTS, CRON_COMMENT, USER
from crontab import CronTab
import logging
from pathlib import Path
import subprocess
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#.......................................................................


def subprocess_run(cmd:str,
                   capture_output=True,
                   check:bool=False,
                   text=True,
                   shell=True,
                  ) -> subprocess.CompletedProcess:
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
        data = None

    return data


def make_executable(sh_path:Path) -> None:
    """Alternative to os.chmod(sh_path, stat.S_IXUSR): permission denied."""

    cmd = f"chmod +x {sh_path}"
    try:
        p = subprocess_run(cmd,
                           capture_output=False,
                           check=True,
                           )
    except subprocess.CalledProcessError as e:
        logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {e}")
        raise


CRON_SH_NAME = "crontab_sh"
def create_cron_sh(conda_env:str,
                   benchmarks_dir:Path,
                   job_name:str,
                   n_active:int,
                   sentinel_file:str
                  ) -> Path:
    """
    Create the batch-submitting bash script that crontab will use in
    benchmarks_dir as 'crontab_sh'.
    Return its path
    """

    cli = ENTRY_POINTS["child"]
    sh_fstr = """
#!/usr/bin/env sh

#conda run -n <mce> <cli> -benchmarks_dir <dir> -job_name <foo> -n_active <n> -sentinel_file <sf>.

conda run -n {} {} -benchmarks_dir {} -job_name {} -n_active {} -sentinel_file {}
"""
    sh_path = benchmarks_dir.joinpath(CRON_SH_NAME)
    with open(sh_path , "w") as fh:
        fh.write(sh_fstr.format(conda_env,
                                cli,
                                str(benchmarks_dir),
                                job_name,
                                n_active,
                                sentinel_file))

    make_executable(sh_path)  #needed?
    logger.info(f"Created script for crontab {CRON_SH_NAME!r} in {benchmarks_dir}\n")

    return sh_path


def build_cron_path():
    """
    DEPRECATE?
    Switched to creating an ad-hoc bash script that's calling
    the launching cli using conda run + a conda env name;
    => presumably, a more specific path is not needed.

    Replicate PATH as per jmao:
    PATH=/home/jmao/miniconda3/bin: \
    /home/jmao/Stable-MCCE/bin: \
    /home/jmao/bin: \
    /home/jmao/miniconda3/condabin: \
    /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin

    On isis:
    (base) cchenal@isis:~/projects$ which step1.py
    /home/mcce/Stable-MCCE/bin/step1.py => keep in path?
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


def build_cron_cmd(sh_path:Path):
    return f"#{CRON_COMMENT}\n* * * * * {str(sh_path)} > /tmp/cron.log 2>&1\n"


def create_crontab(cron_cmd:str, cron_path:str=None):
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
    logger.info(f"Crontab text:\n{crontab_txt}")

    cron_out = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE)
    cron_out.communicate(input=bytes(crontab_txt, 'utf-8'))

    logger.info("User's cron jobs, if any:")
    for job in cron:
        logger.info(f"{job}\n")

    return
