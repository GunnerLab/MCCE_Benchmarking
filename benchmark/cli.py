"""
Module: cli.py

Command line interface for MCCE benchmarking.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
# import class of files resources and constants:
from benchmark import APP_NAME, BENCH, MCCE_EPS, N_SLEEP, N_ACTIVE, MCCE_OUTPUTS
from benchmark import job_setup, batch_submit
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


mdl_logger = logging.getLogger(f"{APP_NAME}.{__name__}")


#.......................................................................
CLI_NAME = "mcce_bench"  # as per pyproject.toml, same as APP_NAME

SUB_CMD0 = "data_setup"
SUB_CMD1 = "from_step1"

USAGE = f"{CLI_NAME} <sub-command for simulation start> <related args>\n"
DESC = f"""
    Launch a MCCE benchmarking job using curated structures from the pKa Database v1.

    The main command is {CLI_NAME!r} along with one of 3 sub-commands,
    which distinguishes the starting point for the MCCE simulation.
    - Sub-command {SUB_CMD0!r}: setup data folders;
    - Sub-command {SUB_CMD1!r}: starts from step1 -> step4;

"""
HELP_0 = f"Sub-command {SUB_CMD0!r} for preparing `benchmarks_dir/clean_pdbs folder."
HELP_1 = f"Sub-command {SUB_CMD1!r} for starting the MCCE simulation from step1."


def bench_data_setup(args):
    """Benchmark data setup 'data_setup' sub-command."""

    mdl_logger.info("Preparing pdbs folder.")
    job_setup.setup_pdbs_folder(args.benchmarks_dir)

    return


def bench_from_step1(args):
    """Benchmark script wrting and launch for 'from_step1' sub-command."""
    # write <job_name>.sh
    # launch

    if not args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS).exists():
        msg = f"Missing {BENCH.CLEAN_PDBS!r}: Re-run subcommand {SUB_CMD0!r}, perhaps."
        mdl_logger.exception(msg)
        raise FileNotFoundError(msg)

    mdl_logger.info("Deleting pK.out files, if any.")
    delete_pkout(args.benchmarks_dir)

    mdl_logger.info("Write fresh book file.")
    audit.rewrite_book_file(book)

    mdl_logger.info("Writing script for job_name.")
    sh_path = job_setup.write_run_script(args.benchmarks_dir,
                                         args.job_name,
                                         #sh_template
                                         )

    mdl_logger.info("Submiting batch of jobs.")
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
                                  help = "The 2 choices for the benchamarking start: step1 or step3.",
                                  dest = "subparser_name"
                                 )

    sub0 = subparsers.add_parser(SUB_CMD0,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_0)
    sub0.add_argument(
        "-benchmarks_dir",
        default = Path("mcce_benchmarks"),
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        "clean_pdbs" folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: %(default)s.
        """
    )
    # bind sub0 parser with its related function:
    sub0.set_defaults(func=bench_data_setup)

    sub1 = subparsers.add_parser(SUB_CMD1,
                                 parents = [sub0],
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_1)
    sub1.add_argument(
        "-job_name",
        type = str,
        default = BENCH.DEFAULT_JOB,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the 'run.sh' script in 'benchmarks_dir' that launches the MCCE simulation
        in 'benchmarks_dir/clean_pdbs' subfolders; default: %(default)s.
        """
    )
    sub1.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2, this file is 'step2_out.pdb'; default: %(default)s.
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
        default = MCCE_EPS,
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
    # bind sub1 parser with its related function:
    sub1.set_defaults(func=bench_from_step1)


    return p


def bench_cli(argv=None):
    """
    Command line interface for MCCE benchmarking.
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
