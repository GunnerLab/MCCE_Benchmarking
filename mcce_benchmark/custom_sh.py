#!/usr/bin/env python

"""
Module: custom_sh.py

Functions for building a custom script when cli args are not all defaults.

* Custom template (SH_TEMPLATE):
 ```
 #!/bin/bash

 step1.py prot.pdb {wet}{noter}{d}{s1_norun}{u}
 step2.py {conf_making_level}{d}{s2_norun}{u}
 step3.py {c}{x}{f}{p}{r}{d}{s3_norun}{u}
 step4.py --xts {titr_type}{i}{interval}{n}{ms}{s4_norun}{u}

 sleep 10
 ```
=> recovers the flexibility of each step<n>.py cli.
"""

from argparse import Namespace as argNamespace
from mcce_benchmark import BENCH
from enum import Enum
import logging
from pathlib import Path
import subprocess


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#.................................................................
# For testing:
# To check script is run inside a PDB folder:
RUN_SH_TEST_ECHO = """
#!/bin/bash

echo "Using RUN_SH_TEST_ECHO as script: $PWD"
"""

# To test submit_script without running anything:
RUN_SH_NORUN = """
#!/bin/bash

step1.py prot.pdb --norun
"""
#...............................................................................
# for custom script:
SH_TEMPLATE = """
 #!/bin/bash

 step1.py prot.pdb {wet}{noter}{d}{s1_norun}{u}
 step2.py {conf_making_level}{d}{s2_norun}{u}
 step3.py {c}{x}{f}{p}{r}{d}{s3_norun}{u}
 step4.py --xts {titr_type}{i}{interval}{n}{ms}{s4_norun}{u}

 sleep 10
"""

class ScriptChoices(str, Enum):
    TEST_ECHO = RUN_SH_TEST_ECHO
    NORUN = RUN_SH_NORUN
    CUSTOM = SH_TEMPLATE


cli_to_mcce_opt = {"wet":"dry",
                   "conf_making_level":"l",
                   "interval":"d",
                   "titr_type":"t",
                   "s1_norun":"norun",
                   "s2_norun":"norun",
                   "s3_norun":"norun",
                   "s4_norun":"norun",
                  }

# cli defaults per step:
defaults_per_step = {
"s1": {"wet":False, "noter":False, "d":4.0, "s1_norun":False, "u":""},
"s2": {"conf_making_level":1, "d":4.0, "s2_norun":False, "u":""},
"s3": {"c":[1, 99999], "x":"delphi", "f":"/tmp", "p":1, "r":False,
       "d":4.0, "s3_norun":False, "u":""},
"s4": {"titr_type":"ph", "i":0.0, "interval":1.0, "n":15, "ms":False,
       "s4_norun":False, "u":""},
}
# combined:
all_default_opts = {}
for S in defaults_per_step:
    all_default_opts.update(((k, v) for k, v in defaults_per_step[S].items()))


def cli_args_to_dict(sh_args:argNamespace) -> dict:
    """Only return mcce steps args."""

    excluded_keys = ["subparser_name", "benchmarks_dir", "n_pdbs",
                     "sentinel_file", "job_name","func"]
    d_args = {k:v for k, v in vars(sh_args).items() if k not in excluded_keys}
    return d_args


def all_opts_are_defaults(sh_args:argNamespace) -> bool:
    """Return True if sh_args are default in all the steps,
    else return False. Purpose: determine whether to write
    a custom script or use the default one.
    """

    # holds mcce options only
    d_sh_args = cli_args_to_dict(sh_args)
    is_default = True
    for opt in d_sh_args:
        is_default = (is_default
                      and d_sh_args[opt] == all_default_opts.get(opt)
        )
        if not is_default:  # done
            return False

    return True


def populate_custom_template(job_args:argNamespace) -> str:
    """Return the custom template string filled with appropriate values."""

    d_args = cli_args_to_dict(job_args)
    d_all = {}
    # note: trailing spaces needed:
    v = d_args.pop("wet")
    d_all["wet"] = "" if v else "--dry "
    v = d_args.pop("noter")
    d_all["noter"] = "--noter " if v else ""
    for s in ["s1_norun","s2_norun","s3_norun","s4_norun"]:
        v = d_args.pop(s)
        d_all[s] = "--norun " if v else ""
    # all remaining:
    for k in d_args:
        v = d_args.get(k, "")
        if str(v) == str(all_default_opts[k]):
            d_all[k] = ""
        else:
            d_all[k] = f"-{cli_to_mcce_opt.get(k, k) } {v }"

    body = ScriptChoices.CUSTOM.value.format(**d_all)

    return body


def write_run_script_from_template(benchmarks_dir:str,
                                   job_name:str,
                                   script_template:ScriptChoices = ScriptChoices.CUSTOM,
                                   job_args:argNamespace = None) -> None:
    """
    Write a custom shell script in <benchmarks_dir>/clean_pdbs/ to submit steps 1-4 when
    script_template is CUSTOM, or perform tests otherwise. job_args can be None for
    templates other than CUSTOM.
    Delete a pre-exisitng script with the same name.

    Args:
    script_template (ScriptChoices enum): one of TEST_ECHO, NORUN, CUSTOM (default)
    """

    benchmarks_dir = Path(benchmarks_dir)
    user_pdbs = benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not user_pdbs.exists():
        msg = f"{benchmarks_dir} does not have a 'clean_pdbs' subfolder: rerun `setup_pdbs_folder` maybe?"
        logger.error(msg)
        raise FileNotFoundError(msg)

    if not job_name:  # empty str"
        logger.error("'job_name' is required to have a value.")
        raise ValueError("'job_name' is required to have a value.")

    if job_name == "default_run":
        msg = f"'job_name' cannot be 'default_run' for a custom script."
        logger.error(msg)
        raise ValueError(msg)

    if script_template is ScriptChoices.CUSTOM:
        if job_args is None:
            msg = f"job_args cannot be None when using the CUSTOM template."
            logger.error(msg)
            raise ValueError(msg)

        sh_text = populate_custom_template(job_args)
    else:
        sh_text = script_template.value

    sh_path = user_pdbs.joinpath(f"{job_name}.sh")
    if sh_path.exists():
        sh_path.unlink()

    with open(sh_path , "w") as fh:
        fh.write(sh_text)

    # make script executable, permission denied w/ os.chmod(sh_path, stat.S_IXUSR)
    try:
        p = subprocess.run(f"chmod +x {sh_path}",
                           capture_output=False,
                           check=True,
                           shell=True,
                           )
    except subprocess.CalledProcessError as e:
        logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {e}")
        raise

    return
