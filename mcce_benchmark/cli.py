#!/usr/bin/env python

"""
Module: cli.py

Command line interface for MCCE benchmarking.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
from crontab import CronTab
# import class of files resources and constants:
from mcce_benchmark import BENCH, DEFAULT_DIR, MCCE_EPS, N_SLEEP, N_ACTIVE, ENTRY_POINTS, USER_ENV, CRON_COMMENT
from mcce_benchmark import apply_header_logger, audit, job_setup, batch_submit, scheduling
#import build_cron_path, build_cron_cmd, create_crontab, 

from IPython.core.formatters import format_display_data
import logging
from pathlib import Path
import sys

apply_header_logger()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#.......................................................................


CLI_NAME = ENTRY_POINTS["parent"] # as per pyproject.toml entry point

SUB_CMD1 = "data_setup"
HELP_1 = "Sub-command for preparing `<benchmarks_dir>/clean_pdbs folder."

SUB_CMD2 = "script_setup"
HELP_2 = "Sub-command for setting up the job_name_run.sh script."

#TODO?:
# - cmd3 name: change to "batch_schedule"?
# - add arg --do_not_schedule => for very small jobs?
#
SUB_CMD3 = "launch_batch"
HELP_3 = "Sub-command for launching a batch of jobs."

DESC = f"""
Description:
Launch a MCCE benchmarking job using curated structures from the pKa Database v1.

The main command is {CLI_NAME!r} along with one of 3 sub-commands:
- Sub-command 1: {SUB_CMD1!r}: setup data folders;
- Sub-command 2: {SUB_CMD2!r}: setup the run script to run mcce steps 1 through 4;
- Sub-command 3: {SUB_CMD3!r}: launch a batch of jobs;

Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues

"""
bench_default_jobname = BENCH.DEFAULT_JOB

USAGE = f"""
{CLI_NAME} <+ sub-command :: one of [{SUB_CMD1}, {SUB_CMD2}, {SUB_CMD3}]> <related args>\n
Examples for current implementation (Beta):

1. Data setup
 - Using defaults (benchmarks_dir= {DEFAULT_DIR}):
   >mccebench data_setup

 - Using a different folder name:
   >mccebench data_setup -benchmarks_dir <different name>

2. Script setup
 - Using defaults (benchmarks_dir= {DEFAULT_DIR}; job_name= {bench_default_jobname}):
   >mccebench script_setup

 - Using non-default option(s):
   >mccebench script_setup -job_name <my_job_name>
   >mccebench script_setup -benchmarks_dir <different name> -job_name <my_job_name>

3. Submit batch of jobs
 - Using defaults (benchmarks_dir= {DEFAULT_DIR};
                   job_name= {bench_default_jobname};
                   n_active= {N_ACTIVE};
                   sentinel_file= pK.out):
   >mccebench launch_batch

 - Using non-default option(s):
   >mccebench launch_batch -n_active <jobs to maintain>
   >mccebench launch_batch -job_name <my_job_name> -sentinel_file step2_out.pdb
"""


def args_to_str(args:argNamespace) -> str:
    """Return cli args to string.
    Note: Using format_display_data output is as in nbk: 'func' object ref is
    in readeable form instead of uid.
    """

    return f"{CLI_NAME} args:\n{format_display_data(vars(args))[0]['text/plain']}\n"


def bench_data_setup(args:argNamespace):
    """Benchmark cli function for 'data_setup' sub-command.
    Setup the pdbs data in args.benchmarks_dir.
    """

    logger.info(args_to_str(args))
    logger.info(f"Preparing pdbs folder & data in {args.benchmarks_dir}.")
    job_setup.setup_pdbs_folder(args.benchmarks_dir)
    logger.info("Setup over.")

    return


def bench_script_setup(args:argNamespace) -> None:
    """Benchmark cli function for 'script_setup' sub-command.
    PRE-REQS: args.benchmarks_dir & clean_pdbs folders exist as previously
    created via > mccebench data_setup command.
    Processing steps:
     1. Write fresh book file
     2. Write script for args.job_name
     3. Delete all previous sentinel files, if any
    """

    in_benchmarks = Path.cwd().name == args.benchmarks_dir.name
    if in_benchmarks:
        args.benchmarks_dir = Path.cwd()

    clean_pdbs_dir = args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not clean_pdbs_dir.exists():
        msg = f"Missing {BENCH.CLEAN_PDBS!r} folder in {args.benchmarks_dir}:\nRe-run subcommand {SUB_CMD1!r}, perhaps?"
        logger.exception(msg)
        raise FileNotFoundError(msg)

    logger.info(args_to_str(args))

    book = clean_pdbs_dir.joinpath(BENCH.Q_BOOK)
    logger.info("Write fresh book file.")
    audit.rewrite_book_file(book)

    logger.info(f"Writing script for {args.job_name!r} job.")
    job_setup.write_run_script(args.benchmarks_dir, args.job_name)

    logger.info("Deleting previous sentinel files, if any.")
    job_setup.delete_sentinel(args.benchmarks_dir, args.sentinel_file)
    return


def schedule_job(launch_args:argNamespace):
    """Create a contab entry for batch_submit.py with `launch_args`"""

    sh_path = scheduling.create_cron_sh(launch_args.conda_env,
                                        launch_args.benchmarks_dir,
                                        launch_args.job_name,
                                        launch_args.n_active,
                                        launch_args.sentinel_file
                                       )
    logger.info("Created the bash script for crontab.")

    #pa = scheduling.build_cron_path()  #previously
    cron_cmd = scheduling.build_cron_cmd(sh_path)
    scheduling.create_crontab(cron_cmd)
    logger.info("Scheduled batch submission with crontab every minute.")


# bench_batch_schedule
def bench_launch_batch(args:argNamespace) -> None:
    """Benchmark cli function for 'launch_batch' sub-command.
    PRE-REQS:
    1. args.benchmarks_dir & clean_pdbs folders exist as previously
       created via > mccebench data_setup command.
    2. args.job_name script exists as previously created via
       mccebench script_setup command.
    """

    in_benchmarks = Path.cwd().name == args.benchmarks_dir.name
    if in_benchmarks:
        args.benchmarks_dir = Path.cwd()

    logger.info(args_to_str(args))

    logger.info("Submiting batch of jobs.")
    DEBUG = False
    if DEBUG:
        logger.info("Debug mode: batch_submit.launch_job not called")
    else:
        logger.info("Beta mode: scheduling job")
        # submit 1st with batch_submit.launch_job:
        batch_submit.launch_job(args.benchmarks_dir,
                                args.job_name,
                                args.n_active,
                                args.sentinel_file)
        # with crontab; FIX: fails silently
        schedule_job(args)

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
        epilog = ">>> END of %(prog)s",
    )
    subparsers = p.add_subparsers(required = True,
                                  title = f"{CLI_NAME} sub-commands",
                                  description = "Sub-commands of MCCE benchmarking cli.",
                                  help = """The 3 choices for the benchmarking process:
                                  1) Setup data: {SUB_CMD1}
                                  2) Setup script: {SUB_CMD2}
                                  3) Batch-run mcce steps 1 through 4: {SUB_CMD3}""",
                                  dest = "subparser_name"
                                 )

    # data_setup
    sub1 = subparsers.add_parser(SUB_CMD1,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_1)
    sub1.add_argument(
        "-benchmarks_dir",
        default = Path(DEFAULT_DIR).resolve(),
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        "clean_pdbs" folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: mcce_benchmarks.
        """
    )
    # bind subparser with its related function:
    sub1.set_defaults(func=bench_data_setup)

    # script_setup
    sub2 = subparsers.add_parser(SUB_CMD2,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_2)
    sub2.add_argument(
        "-benchmarks_dir",
        default = Path(DEFAULT_DIR).resolve(),
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        "clean_pdbs" folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: mcce_benchmarks.
        """
    )
    sub2.add_argument(
        "-job_name",
        type = str,
        default = bench_default_jobname,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'benchmarks_dir' that launches the MCCE simulation
        in 'benchmarks_dir/clean_pdbs' subfolders; default: %(default)s.
        """
    )
    sub2.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2 [future implementation], this file is 'step2_out.pdb'; default: %(default)s.
        """
    )
    sub2.add_argument(
        "-wet",
        default = False,
        help = "Keep water molecules.",
    )
    sub2.add_argument(
        "-norun",
        default = False,
        help = "Create run.prm without running the step",
    )
    #sub2.add_argument(
    #    "-e",
    #    metavar = "/path/to/mcce",
    #    default = "mcce",
    #    help = "Location of the mcce executable, i.e. which mcce; default: %(default)s.",
    #)
    sub2.add_argument(
        "-eps",
        metavar = "epsilon",
        default = MCCE_EPS,
        help = "Protein dielectric constant; default: %(default)s.",
    )
    sub2.add_argument(
        "-u",
        metavar = "Comma-separated list of Key=Value pairs.",
        default = "",
        help = """User selected, comma-separated KEY=var pairs from run.prm; e.g.:
        -u HOME_MCCE=/path/to/mcce_home,H2O_SASCUTOFF=0.05,EXTRA=./extra.tpl; default: %(default)s.
        Note: No space after a comma!"""
    )
    sub2.set_defaults(func=bench_script_setup)

    # launch_batch
    sub3 = subparsers.add_parser(SUB_CMD3,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_3)
    sub3.add_argument(
        "-conda_env",
        default = "base",
        type = str,
        help = """Name of the conda environment where mcce_benchmark was installed."""
    )
    sub3.add_argument(
        "-benchmarks_dir",
        default = Path(DEFAULT_DIR).resolve(),
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        "clean_pdbs" folder reside. The directory is created if it does not exists unless this cli is
        called within that directory; default: mcce_benchmarks.
        """
    )
    sub3.add_argument(
        "-job_name",
        type = str,
        default = bench_default_jobname,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'benchmarks_dir' that launches the MCCE simulation
        in 'benchmarks_dir/clean_pdbs' subfolders; default: %(default)s.
        """
    )
    sub3.add_argument(
        "-n_active",
        type = int,
        default = N_ACTIVE,
        help = """The number of jobs to keep launching; default: %(default)s.
        """
    )
    sub3.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2 [future implementation], this file is 'step2_out.pdb'; default: %(default)s.
        """
    )
    sub3.set_defaults(func=bench_launch_batch)

    return p


def bench_cli(argv=None):
    """
    Command line interface for MCCE benchmarking entry point 'mccebench'.
    """

    cli_parser = bench_parser()
    args = cli_parser.parse_args(argv)
    args.func(args)

    return


if __name__ == "__main__":

    bench_cli(sys.argv[1:])
