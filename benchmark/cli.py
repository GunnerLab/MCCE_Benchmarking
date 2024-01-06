# WIP - copied from other project
"""
Module: cli.py


"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
# import class of files resources and constants:
from benchmark import BENCH, MCCE_OUTPUTS
from benchmark import cleanup
import numpy as np
import os
import pandas as pd
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Union, TextIO


# TODO:
# Implement logging

# 1. ID cli parameters
# 2. main fns:
#    setup_bench_dir
#    launch_batch

#.......................................................................
mcce_step_options = {
    "S1":{"msg":"Run mcce step 1, premcce to format PDB file to MCCE PDB format.",
          "--noter": {"default":False, "help":"Do not label terminal residues (for making ftpl).", "action":"store_true"},
          "--dry":   {"default":False, "help":"Delete all water molecules.", "action":"store_true"},
          },
    "S2":{"msg":"Run mcce step 2, make side chain conformers from step1_out.pdb.",
          "-l":      {"metavar":"level",
                      "type":int, "default":1,
                      "help":"Conformer level 1=quick (default), 2=medium, 3=full"},
          },
    "S3":{"msg":"Run mcce step 3, energy calculations, with multiple threads.",
          # should have been --r:
          "-r":      {"default":False, "help":"refresh opp files and head3.lst without running delphi", "action":"store_true"},
          "-c":      {"metavar":"('conf start', 'conf end')",
                      "type":int,
                      "default":[1, 99999], "nargs":2,
                       "help":"starting and ending conformer, default to 1 and 9999"},
          "-f":      {"metavar":"tmp folder", "default":"/tmp", "hel":"delphi temporary folder, default to /tmp"},
          "-p":      {"metavar":"processes", "type":int, "default":1,
                      "help":"run mcce with p number of processes; default: %(default)s."},
          },
    "S4":{"msg":"Run mcce step 4, Monte Carlo sampling to simulate a titration.",
          "--xts":   {"default":False, "help":"Enable entropy correction, default is false", "action":"store_true"},
          "--ms":    {"default":False, "help":"Enable microstate output", "action":"store_true"},
          "-t":      {"metavar":"ph or eh", "default":"ph", "help":"titration type: pH or Eh."},
          "-i":      {"metavar":"initial ph/eh", "default":"0.0", "help":"Initial pH/Eh of titration; default: %(default)s."},
          "-d":      {"metavar":"interval", "default":"1.0", "help":"titration interval in pJ or mV; default: %(default)s."},
          "-n":      {"metavar":"steps", "default":"15", "help":"number of steps of titration; default: %(default)s."},
          }
}


CLI_NAME = "mcce_bench"  # as per pyproject.toml
SUB_CMD1, SUB_CMD2 = "from_step1", "from_step3"
USAGE = f"{CLI_NAME} <sub-command for simulation start> <related args>\n"
DESC = f"""
    Launch a MCCE benchmarking job using curated structures from the pKa Database v1.

    The main command is {CLI_NAME!r} along with one of two sub-commands,
    which distinguishes the starting point for the MCCE simulation.
    - Sub-command {SUB_CMD1!r}: starts from step1 -> step4;
    - Sub-command {SUB_CMD2!r}: starts from step3 -> step4 :: NOT YET IMPLEMENTED!

"""
HELP_1 = f"Sub-command {SUB_CMD1!r} for starting the MCCE simulation from step1."
HELP_2 = f"Sub-command {SUB_CMD2!r} for starting the MCCE simulation from step3."


def bench_from_step1(args):
    """Benchmark setup and launch for 'from_step1' sub-command."""
    # TODO
    # setup folders
    # write <job_name>.sh
    # launch
    pass


def bench_from_step3(args):
    """Benchmark setup and launch for 'from_step3' sub-command."""
    # TODO later
    pass


def bench_parser():
    """Command line arguments parser with sub-commands for use in benchmarking.
    """

    def arg_valid_dirpath(p: str):
        """Return resolved path from the command line."""
        if not len(p):
            return None
        return Path(p).resolve()

    p = ArgumentParser(
        prog = f"{CLI_NAME} ",
        description = DESC,
        usage = USAGE,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = ">>> END of %(prog)s.",
    )
    subparsers = p.add_subparsers(required = True,
                                  title = "Benchmarking sub-commands",
                                  description = "Subcommands of benchamrking MCCE.",
                                  help = "The 2 choices for the benchamarking start: step1 or step3.",
                                  dest = "subparser_name"
                                 )

    sub1 = subparsers.add_parser(SUB_CMD1,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_1)
    sub1.add_argument(
        "benchmark_dir",
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); required.
        If the directory does not exists in the location where this cli is called, then it is
        created. Recommended name: "mcce_benchmarks"; this is where all subsequent jobs will
        reside as subfolders.
        """
    )
    sub1.add_argument(
        "job_name",
        type = str,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to name the job folder in 'benchmark_dir' and the script that launches the
        MCCE simulation in ./clean_pdbs folder.
        """
    )
    # always 'prot.pdb' as per soft-link setup: ln -s DIR/dir.pdb prot.pdb
    #sub1.add_argument(
    #    "-prot",
    #    metavar = "pdb",
    #    default = "prot.pdb",
    #    help = "The name of the pdb; default: %(default)s.",
    )
    sub1.add_argument(
        "--dry",
        default = False,
        help = "No water molecules.",
        action = "store_true"
    )
    sub1.add_argument(
        "--norun",
        default = False,
        action = "store_true",
        help = "Create run.prm without running the step"
    )
    sub1.add_argument(
        "-e",
        metavar = "/path/to/mcce",
        default = "mcce",
        help = "Location of the mcce executable, i.e. which mcce; default: %(default)s.",
    )
    sub1.add_argument(
        "-eps",
        metavar = "epsilon",
        default = "4.0",
        help = "Protein dielectric constant; default: %(default)s.",
    )
    sub1.add_argument(
        "-u",
        metavar = "Comma-separated list of Key=Value pairs.",
        default = "",
        help = """Any comma-separated KEY=var from run.prm; e.g.:
        -u HOME_MCCE=/path/to/mcce_home,H2O_SASCUTOFF=0.05,EXTRA=./extra.tpl; default: %(default)s.
        Note: No space after a comma!"""
    )

    #sub1.add_argument(
    #    "-msout_file",
    #    type = str,
    #    default = "pH7eH0ms.txt",
    #    help = "Name of the mcce_dir/ms_out/ microstates file, `pHXeHYms.txt'; default: %(default)s.""",
    #)

    ################################################################################
    #TODO:
    # Add specific step options from mcce_step_options



    # bind sub1 parser with its related function:
    sub1.set_defaults(func=bench_from_step1)

    # later:
    #sub2 = subparsers.add_parser(SUB_CMD2,
    #                              formatter_class = RawDescriptionHelpFormatter,
    #                              help=HELP_2)

    return p




def bench_cli(argv=None):
    """
    Command line interface to:

    """

    cli_parser = bench_parser()
    args = cli_parser.parse_args(argv)
    #if argv is None:
    #    cli_parser.print_help()
    #    return
    args.func(args)

    return


if __name__ == "__main__":
    bench_cli(sys.argv[1:])
