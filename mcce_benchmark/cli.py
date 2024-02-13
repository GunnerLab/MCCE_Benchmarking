#!/usr/bin/env python

"""
Module: cli.py

Command line interface for MCCE benchmarking.
Main entry point: ENTRY_POINTS["main"] ("mccebench")
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
from crontab import CronTab
# import class of files resources and constants:
from mcce_benchmark import BENCH, DEFAULT_DIR, MCCE_EPS, N_ACTIVE, ENTRY_POINTS
from mcce_benchmark import create_log_header, audit, job_setup, batch_submit, scheduling, custom_sh
from IPython.core.formatters import format_display_data
import logging
from pathlib import Path
import sys


create_log_header()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#.......................................................................


CLI_NAME = ENTRY_POINTS["main"] # as per pyproject.toml entry point

SUB_CMD1 = "data_setup"
HELP_1 = "Sub-command for preparing `<benchmarks_dir>/clean_pdbs folder."

SUB_CMD2 = "script_setup"
HELP_2 = "Sub-command for setting up the job_name_run.sh script."

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

1. Data setup; sub-command: {SUB_CMD1}
   PURPOSE: Creation of a data set with this structure: <benchmarks_dir>/clean_pdbs,
            including the all the curated pdbs from the pKaDB in their respective
            folders, and all ancillary files.
   THIS STEP IS NOT NEEDED if you want to compare two mcce runs that do not use any of the above pdbs.

   - Using defaults (benchmarks_dir= {DEFAULT_DIR}):
   >{CLI_NAME} {SUB_CMD1}

 - Using a different folder name:
   >{CLI_NAME} {SUB_CMD1} -benchmarks_dir <different name>

2. Script setup; sub-command: {SUB_CMD2}
   PURPOSE: Creation of a custom mcce run script for steps 1-4 if any of the command line
            options differ from the default ones. If only the job_name differs, the
            default run script is soft linked to that name, which will be identifiable
            in the user's running processes list. For this reason, it is recommnended
            customize the job_name for each benchmark submission else all processes will
            show "default_run.sh".

 - Using defaults (benchmarks_dir= {DEFAULT_DIR}; job_name= {bench_default_jobname}):
   >{CLI_NAME} {SUB_CMD2}

 - Using non-default option(s):
   >{CLI_NAME} {SUB_CMD2} -job_name <my_job_name>
   >{CLI_NAME} {SUB_CMD2} -benchmarks_dir <different name> -job_name <my_job_name>

3. Submit batch of jobs; sub-command: {SUB_CMD3}
 - Using defaults (benchmarks_dir= {DEFAULT_DIR};
                   job_name= {bench_default_jobname};
                   n_active= {N_ACTIVE};
                   sentinel_file= pK.out):
   >{CLI_NAME} {SUB_CMD3}

 - Using non-default option(s):
   >{CLI_NAME} {SUB_CMD3} -n_active <jobs to maintain>
   >{CLI_NAME} {SUB_CMD3} -job_name <my_job_name> -sentinel_file step2_out.pdb
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
    PRE-REQS: args.benchmarks_dir & clean_pdbs folders exist (as they would
    if 'mccebench data_setup' command was used prior to this step).
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
        logger.error(msg)
        raise FileNotFoundError(msg)

    logger.info(args_to_str(args))

    book = clean_pdbs_dir.joinpath(BENCH.Q_BOOK)
    logger.info("Write fresh book file.")
    audit.rewrite_book_file(book)

    logger.info(f"Writing script for {args.job_name!r} job.")
    # determine if args are all defaults
    use_default_sh = custom_sh.all_opts_are_defaults(args)
    if use_default_sh:
        job_setup.write_default_run_script(args.benchmarks_dir, args.job_name)
    else:
        custom_sh.write_run_script_from_template(args.benchmarks_dir,
                                                 args.job_name,
                                                 job_args = args)

    logger.info("Deleting previous sentinel files, if any.")
    job_setup.delete_sentinel(args.benchmarks_dir, args.sentinel_file)
    return


# bench_batch_schedule
def bench_launch_batch(args:argNamespace) -> None:
    """Benchmark cli function for 'launch_batch' sub-command.
    PRE-REQS:
    1. args.benchmarks_dir & clean_pdbs folders exist as previously
       created via 'mccebench data_setup' command.
    2. args.job_name script exists as previously created via
       mccebench script_setup command.
    """

    #TODO:
    #Output script to log again in case it was manualy modified

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
        # temp: submit 1st with batch_submit.launch_job:
        batch_submit.launch_job(args.benchmarks_dir,
                                args.job_name,
                                args.n_active,
                                args.sentinel_file)
        # with crontab; FIX: fails silently
        scheduling.schedule_job(args)

    return


def bench_parser():
    """Command line arguments parser with sub-commands for use in benchmarking.
    """

    def arg_valid_dirpath(p: str):
        """Return resolved path from the command line."""
        if not len(p):
            return None
        return Path(p).resolve()

    # parent parser
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
    # sentinel_file (e.g. pK.out) is part of script setup to ensure it is deleted prior to using launch sub-command.
    sub2.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2 [future implementation], this file is 'step2_out.pdb'; default: %(default)s.
        """
    )
    #step1.py prot.pdb {wet} {noter} {d} {s1_norun} {u}
    sub2.add_argument(
        "-wet",
        type = bool,
        default = False,
        help = "Keep water molecules.",
    )
    sub2.add_argument(
        "--noter",
        default = False,
        help = "Do not label terminal residues (for making ftpl).", action="store_true"
    )
    # common to all steps:
    sub2.add_argument(
        "-u", metavar = "Key=Value",
        type = str, default = "",
        help = """
        User selected, comma-separated KEY=var pairs from run.prm; e.g.:
        -u HOME_MCCE=/path/to/mcce_home,H2O_SASCUTOFF=0.05,EXTRA=./extra.tpl; default: %(default)s.
        Note: No space after a comma!"""
    )

    # norun option for each steps:
    sub2.add_argument(
        "-s1_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 1."
    )
    sub2.add_argument(
        "-s2_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 2."
    )
    sub2.add_argument(
        "-s3_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 3."
    )
    sub2.add_argument(
        "-s4_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 4."
    )
    # steps 1-3:
    sub2.add_argument(
        "-d", metavar = "epsilon",
        type = float,
        default = 4.0,
        help = "protein dielectric constant for delphi; %(default)s."
    )

    #step2.py {conf_making_level} {d} {s2_norun} {u}
    sub2.add_argument(
        "-conf_making_level",
        type = int,
        default = 1,
        help = "conformer level 1: quick, 2: medium, 3: comprehensive; default: %(default)s.")

    #step3.py {c} {x} {f} {p} {r} {d} {s3_norun} {u}
    sub2.add_argument(
        "-c", metavar=('start','end'),
        type=int,
        default = [1, 99999], nargs = 2,
        help = "Starting and ending conformer; default: %(default)s."
    )
    sub2.add_argument(
        "-x", metavar = "/path/to/delphi",
        default = "delphi",
        help = "Delphi executable location; default: %(default)s."
    )
    sub2.add_argument(
        "-f", metavar = "tmp folder",
        default = "/tmp",
        help = "Delphi temporary folder; default: %(default)s."
    )
    sub2.add_argument(
        "-p", metavar = "processes",
        type = int,
        default = 1,
        help="Number of processes to use; default: %(default)s."
    )
    #should be --r:
    sub2.add_argument(
        "-r",
        default = False,
        help = "Refresh opp files and head3.lst without running Delphi",
        action = "store_true"
    )

    #step4.py --xts {titr_type} {i} {interval} {n} {ms} {s4_norun} {u}
    sub2.add_argument(
        "-titr_type", metavar="ph or eh",
        type = str,
        default = "ph",
        help = "Titration type, pH or Eh; default: %(default)s."
    )
    sub2.add_argument(
        "-i",
        metavar = "initial ph/eh",
        type = float,
        default = 0.0,
        help="Initial pH/Eh of titration; default: %(default)s."
    )
    sub2.add_argument(
        "-interval", metavar="interval",
        type = float,
        default = 1.0,
        help = "Titration interval in pJ or mV; default: %(default)s."
    )
    sub2.add_argument(
        "-n", metavar = "steps",
        type = int,
        default = 15,
        help = "number of steps of titration; default: %(default)s."
    )
    sub2.add_argument(
        "--ms",
        default = False,
        help = "Enable microstate output",
        action="store_true"
    )
    sub2.set_defaults(func=bench_script_setup)

    # launch_batch
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
    #sub3.add_argument(
    #    "--do_not_schedule",
    #    default = False,
    #    help = "Do schedule via crontab. Use for very small jobs, i.e. number of pdbs < N_ACTIVE.",
    #    action="store_true"
    #)
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
