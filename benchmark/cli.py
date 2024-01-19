"""
Module: cli.py

Command line interface for MCCE benchmarking.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
# import class of files resources and constants:
from benchmark import APP_NAME, BENCH, MCCE_EPS, N_SLEEP, N_ACTIVE, MCCE_OUTPUTS
from benchmark import job_setup, batch_submit, UserLogger
import getpass
import logging
import numpy as np
import os
import pandas as pd
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Union


logger = UserLogger(f"{APP_NAME}.{__name__}")
#.......................................................................


CLI_NAME = "mccebench"  # as per pyproject.toml

SUB_CMD0 = "data_setup"
SUB_CMD1 = "from_step1"

USAGE = f"{CLI_NAME} <+ sub-command :: {SUB_CMD0} or {SUB_CMD1}> <related args>\n"

DESC = f"""
    Launch a MCCE benchmarking job using curated structures from the pKa Database v1.

    The main command is {CLI_NAME!r} along with one of 2 sub-commands,
    which distinguishes the starting point for the MCCE simulation.
    - Sub-command 1: {SUB_CMD0!r}: setup data folders;
    - Sub-command 2: {SUB_CMD1!r}: run mcce steps 1 to 4;

"""
HELP_0 = f"Sub-command {SUB_CMD0!r} for preparing `<benchmarks_dir>/clean_pdbs folder."
HELP_1 = f"Sub-command {SUB_CMD1!r} for starting the MCCE simulation from step1."


def cli_args_to_string(args:argNamespace) -> str:
    """For logging purposes, return cli args to string."""

    out = ",\n".join(f"{k}: {v}" for k, v in vars(args))
    return out


def bench_data_setup(args:argNamespace):
    """Benchmark data setup 'data_setup' sub-command."""

    print(f"Preparing pdbs folder in {args.benchmarks_dir}.")
    logger.debug(f"Preparing pdbs folder in {args.benchmarks_dir}.")
    #job_setup.setup_pdbs_folder(args.benchmarks_dir)

    return


def bench_from_step1(args:argNamespace) -> None:
    """Benchmark script writing and launch for 'from_step1' sub-command."""

    if not args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS).exists():
        msg = f"Missing {BENCH.CLEAN_PDBS!r}: Re-run subcommand {SUB_CMD0!r}, perhaps."
        logger.exception(msg)
        raise FileNotFoundError(msg)

    logger.info("Deleting prevoius pK.out files, if any.")
    delete_pkout(args.benchmarks_dir)

    logger.info("Write fresh book file.")
    audit.rewrite_book_file(book)

    logger.info(f"Writing script for {args.job_name}.")
    sh_path = job_setup.write_run_script(args.benchmarks_dir,
                                         args.job_name,
                                         #sh_template
                                         )
    #TODO:
    #logger.info(f"User parameters for {args.job_name}.")

    logger.info("Submiting batch of jobs.")
    batch_submit.launch_job(args.benchmarks_dir,
                            args.job_name,
                            args.n_active,
                            args.sentinel_file)
    return


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
                                  help = """The 2 choices for the benchmarking process:
                                  1) Setup: {SUB_CMD0}
                                  2) Run mcce steps 1 to 4: {SUB_CMD1}""",
                                  dest = "subparser_name"
                                 )

    sub0 = subparsers.add_parser(SUB_CMD0,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_0)
    sub0.add_argument(
        "-benchmarks_dir",
        default = Path("./mcce_benchmarks"),
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        "clean_pdbs" folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: %(default)s.
        """
    )
    # bind sub0 parser with its related function:
    sub0.set_defaults(func=bench_data_setup)

    sub1 = subparsers.add_parser(SUB_CMD1,
                                 #parents = [sub0],
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_1)
    sub1.add_argument(
        "-benchmarks_dir",
        type = arg_valid_dirpath,
        default = Path("./mcce_benchmarks"),
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        "clean_pdbs" folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: %(default)s.
        """
    )
    sub1.add_argument(
        "-job_name",
        type = str,
        default = BENCH.DEFAULT_JOB,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'benchmarks_dir' that launches the MCCE simulation
        in 'benchmarks_dir/clean_pdbs' subfolders; default: %(default)s.
        """
    )
    sub1.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2 [future implementation], this file is 'step2_out.pdb'; default: %(default)s.
        """
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
        help = "Create run.prm without running the step",
        action = "store_true",
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
        default = MCCE_EPS,
        help = "Protein dielectric constant; default: %(default)s.",
    )
    sub1.add_argument(
        "-u",
        metavar = "Comma-separated list of Key=Value pairs.",
        default = "",
        help = """User selected comma-separated KEY=var from run.prm; e.g.:
        -u HOME_MCCE=/path/to/mcce_home,H2O_SASCUTOFF=0.05,EXTRA=./extra.tpl; default: %(default)s.
        Note: No space after a comma!"""
    )
    # bind sub1 parser with its related function:
    sub1.set_defaults(func=bench_from_step1)


    return p


def bench_cli(argv=None):
    """
    Command line interface for MCCE benchmarking.
    """

    cli_parser = bench_parser()
    args = cli_parser.parse_args(argv)
    args.func(args)

    return


if __name__ == "__main__":
    bench_cli(sys.argv[1:])
