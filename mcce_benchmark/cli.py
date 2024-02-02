"""
Module: cli.py

Command line interface for MCCE benchmarking.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
# import class of files resources and constants:
from mcce_benchmark import BENCH, DEFAULT_DIR, MCCE_EPS, N_SLEEP, N_ACTIVE
from mcce_benchmark import audit, job_setup, batch_submit
from IPython.core.formatters import format_display_data
import logging
from pathlib import Path
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#.......................................................................


CLI_NAME = "mccebench"  # as per pyproject.toml
SUB_CMD1 = "data_setup"
SUB_CMD2 = "script_setup"
SUB_CMD3 = "launch_batch"
HELP_1 = "Sub-command for preparing `<benchmarks_dir>/clean_pdbs folder."
HELP_2 = "Sub-command for setting up the job_name_run.sh script."
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
     3. Delete all previous pK.out files
    """

    in_benchmarks = Path.cwd().name == args.benchmarks_dir.name
    if in_benchmarks:
        args.benchmarks_dir = Path.cwd()

    clean_pdbs_dir = args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS)
    if not clean_pdbs_dir.exists():
        msg = f"Missing {BENCH.CLEAN_PDBS!r} folder in {args.benchmarks_dir}:\nRe-run subcommand {SUB_CMD0!r}, perhaps?"
        logger.exception(msg)
        raise FileNotFoundError(msg)

    logger.info(args_to_str(args))

    book = clean_pdbs_dir.joinpath(BENCH.Q_BOOK)
    logger.info("Write fresh book file.")
    audit.rewrite_book_file(book)

    logger.info(f"Writing script for {args.job_name!r} job.")
    job_setup.write_run_script(args.benchmarks_dir, args.job_name)

    logger.info("Deleting previous pK.out files, if any.")
    job_setup.delete_pkout(args.benchmarks_dir)

    return


def bench_launch_batch(args:argNamespace) -> None:
    """Benchmark cli function for 'launch_batch' sub-command.
    PRE-REQS:
    1. args.benchmarks_dir & clean_padbs folders exist as previously
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
        logger.info("Beta mode: calling batch_submit.launch_job")

        #if args.schedule_job
        #   create crontab file & save in /etc/cron.d ?
        # see https://pypi.org/project/python-crontab/
        # see https://unix.stackexchange.com/questions/458713/how-are-files-under-etc-cron-d-used
        #   PATH=<output of subprocess.run 'echo "$PATH"'
        #   */5 * * * * mccebench launch_batch -benchmarks_dir args.benchmarks_dir -job_name args.job_name -n_active args.n_active -sentinel_file args.sentinel_file > /tmp/cron.log 2>&1
        #else:
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
        "--dry",
        default = False,
        help = "No water molecules.",
        action = "store_true"
    )
    # Beta: the rest of the options are ignored
    sub2.add_argument(
        "--norun",
        default = False,
        help = "Create run.prm without running the step",
        action = "store_true",
    )
    sub2.add_argument(
        "-e",
        metavar = "/path/to/mcce",
        default = "mcce",
        help = "Location of the mcce executable, i.e. which mcce; default: %(default)s.",
    )
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

    sub3 = subparsers.add_parser(SUB_CMD3,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_3)
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
    Command line interface for MCCE benchmarking.
    """

    cli_parser = bench_parser()
    args = cli_parser.parse_args(argv)
    args.func(args)

    return


if __name__ == "__main__":

    bench_cli(sys.argv[1:])
