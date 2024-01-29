"""
code for future implementation
"""

from benchmark import getpass, APP_NAME, BENCH, MCCE_EPS, N_SLEEP, N_ACTIVE
from enum import Enum
import logging
from pathlib import Path
import shutil
import subprocess


logger = logging.getLogger(f"{APP_NAME}.{__name__}")
logger.setLevel(logging.DEBUG)
xtra = {'user':getpass.getuser()}
logger = logging.LoggerAdapter(logger, extra=xtra)


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
RUN_SH_TEST_ECHO = """
#!/bin/bash

echo "Using RUN_SH_TEST_ECHO as script: $PWD"
"""
# To test mcce can run:
RUN_SH_NORUN = """
#!/bin/bash

step1.py prot.pdb --norun
"""

# FUTURE: for testing a new parameter set
RUN_SH_NEW_PARAMS = """
#!/bin/bash
step1.py --dry prot.pdb
step2.py -d {} -u {}  #e.g. HOME_MCCE=/path/to/mcce_home
step3.py -d {} -u {}
step4.py

sleep {}
"""
#.................................................................


# may not need DEFAULT:
class ScriptChoices(Enum):
    TEST_ECHO = RUN_SH_TEST_ECHO
    NORUN = RUN_SH_NORUN
    DEFAULT = RUN_SH_DEFAULTS


def write_run_script_from_template(benchmarks_dir:Path,
                                   job_name:str = "default_run",
                                   script_template:ScriptChoices = None,
                                   job_args:dct = None) -> Path:
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
        logger.exception(msg)
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
                    logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {e}")
                    raise
        else:
            msg = "Missing 'job_name' or no 'script_template' was provided."
            logger.exception(msg)
            raise ValueError(msg)

    return sh_path
