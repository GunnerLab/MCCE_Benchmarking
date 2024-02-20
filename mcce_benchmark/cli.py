#!/usr/bin/env python

"""
Module: cli.py

Command line interface for MCCE benchmarking.
Main entry point: ENTRY_POINTS["main"] ("mccebench")
Then 2 sub-commands:
 1. "setup_job"
     Sub-command for setting up <benchmarks_dir>/clean_pdbs folder & job_name_run.sh script.
 2. "launch_job"
     Sub-command for launching a batch of jobs.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
from crontab import CronTab
# fns defined in init:
from mcce_benchmark import create_log_header, Pathok
# import class of files resources and constants:
from mcce_benchmark import BENCH, DEFAULT_DIR, MCCE_EPS, N_ACTIVE, ENTRY_POINTS
from mcce_benchmark.scheduling import subprocess_run
# modules
from mcce_benchmark import audit, job_setup, batch_submit, scheduling, custom_sh
from IPython.core.formatters import format_display_data
import logging
from pathlib import Path
import subprocess
import sys


create_log_header()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#.......................................................................


CLI_NAME = ENTRY_POINTS["main"] # as per pyproject.toml entry point

SUB_CMD1 = "setup_job"
HELP_1 = "Sub-command for setting up <benchmarks_dir>/clean_pdbs folder & job_name_run.sh script."

SUB_CMD2 = "launch_job"
HELP_2 = "Sub-command for launching a batch of jobs."

DESC = f"""
Description:
Launch a MCCE benchmarking job using curated structures from the pKa Database v1.

The main command is {CLI_NAME!r} along with one of 2 sub-commands:
- Sub-command 1: {SUB_CMD1!r}: setup the dataset and run script to run mcce steps 1 through 4;
- Sub-command 2: {SUB_CMD2!r}: launch a batch of jobs;

Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues

"""
bench_default_jobname = BENCH.DEFAULT_JOB

# chunked to reduce load time ?
USAGE = f"""
{CLI_NAME} <+ sub-command :: one of [{SUB_CMD1}, {SUB_CMD2}]> <related args>\n
Examples for current implementation (Beta):
"""
USAGE = USAGE + f"""
1. Data & script setup; sub-command: {SUB_CMD1}
   PURPOSE: Creation of a data set with this structure: <benchmarks_dir>/clean_pdbs,
            including the all the curated pdbs from the pKaDB in their respective
            folders, and all ancillary files.
            Creation of scripts for running mcce and scheduling.

   - Using defaults (benchmarks_dir= {DEFAULT_DIR}):
   >{CLI_NAME} {SUB_CMD1}

 - Using a different folder name:
   >{CLI_NAME} {SUB_CMD1} -benchmarks_dir <different name>
"""
USAGE = USAGE + f"""
2. Launch runs; sub-command: {SUB_CMD2}
 - Using defaults (benchmarks_dir= {DEFAULT_DIR};
                   job_name= {bench_default_jobname};
                   n_active= {N_ACTIVE};
                   sentinel_file= pK.out):
   >{CLI_NAME} {SUB_CMD2}

 - Using non-default option(s):
   >{CLI_NAME} {SUB_CMD2} -n_active <jobs to maintain>
   >{CLI_NAME} {SUB_CMD2} -job_name <my_job_name> -sentinel_file step2_out.pdb
"""


def args_to_str(args:argNamespace) -> str:
    """Return cli args to string.
    Note: Using format_display_data output is as in nbk: 'func' object ref is
    in readeable form instead of uid.
    """

    return f"{CLI_NAME} args:\n{format_display_data(vars(args))[0]['text/plain']}\n"


def log_mcce_version(pdbs_dir:str) -> None:
    """
    Version from run.log.
    """

    pdbs_fp = Pathok(Path(pdbs_dir), raise_err=False)
    if not pdbs_fp:
        return None
    pdbs = str(pdbs_fp)
    cmd = (f"grep -m1 'Version' {pdbs}/*/run.log | awk -F: '/Version/ "
           + "{print $2 $3}' | sort -u")
    out = subprocess_run(cmd)
    if out is subprocess.CalledProcessError:
        logger.error("Error fetching Version.")
        return

    msg = f"MCCE Version(s) found in run.log files:\n"
    for v in [o.strip() for o in out.stdout.splitlines()]:
        msg = msg + f"\t{v}\n"
    logger.info(msg)

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

    logger.info(f"Preparing pdbs folder & data in {args.benchmarks_dir}.")
    job_setup.setup_pdbs_folder(args.benchmarks_dir)
    logger.info("Setup over.")

    clean_pdbs_dir = Pathok(args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS))

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

    in_benchmarks = Path.cwd().name == args.benchmarks_dir.name
    if in_benchmarks:
        args.benchmarks_dir = Path.cwd()

    logger.info(args_to_str(args))

    #log script text again in case it was manualy modified.
    sh_name = f"{args.job_name}.sh"
    sh_path = Pathok(args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS, sh_name))
    sh_msg = f"Script contents prior to launch:\n{get_script_contents(sh_path)}"
    logger.info(sh_msg)

    logger.info("Submiting batch of jobs.")

    DEBUG = False
    if DEBUG:
        logger.info("Debug mode: batch_submit.launch_job not called")
    else:
        logger.info("Beta mode: scheduling job")
        # temp: submit 1st with batch_submit.launch_job:
        #batch_submit.launch_job(args.benchmarks_dir,
        #                        args.job_name,
        #                        args.n_active,
        #                        args.sentinel_file)

        # with crontab; FIX: fails silently
        scheduling.schedule_job(args)

    # finally:
    log_mcce_version(args.benchmarks_dir.joinpath(BENCH.CLEAN_PDBS))

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
    sub1.add_argument(
        "-job_name",
        type = str,
        default = bench_default_jobname,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'benchmarks_dir' that launches the MCCE simulation
        in 'benchmarks_dir/clean_pdbs' subfolders; default: %(default)s.
        """
    )
    # sentinel_file (e.g. pK.out) is part of script setup to ensure it is deleted prior to using launch sub-command.
    sub1.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2 [future implementation], this file is 'step2_out.pdb'; default: %(default)s.
        """
    )
    #step1.py prot.pdb {wet} {noter} {d} {s1_norun} {u}
    sub1.add_argument(
        "-wet",
        type = bool,
        default = False,
        help = "Keep water molecules.",
    )
    sub1.add_argument(
        "--noter",
        default = False,
        help = "Do not label terminal residues (for making ftpl).", action="store_true"
    )
    # common to all steps:
    sub1.add_argument(
        "-u", metavar = "Key=Value",
        type = str, default = "",
        help = """
        User selected, comma-separated KEY=var pairs from run.prm; e.g.:
        -u HOME_MCCE=/path/to/mcce_home,H2O_SASCUTOFF=0.05,EXTRA=./extra.tpl; default: %(default)s.
        Note: No space after a comma!"""
    )

    # norun option for each steps:
    sub1.add_argument(
        "-s1_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 1."
    )
    sub1.add_argument(
        "-s2_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 2."
    )
    sub1.add_argument(
        "-s3_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 3."
    )
    sub1.add_argument(
        "-s4_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 4."
    )
    # steps 1-3:
    sub1.add_argument(
        "-d", metavar = "epsilon",
        type = float,
        default = 4.0,
        help = "protein dielectric constant for delphi; %(default)s."
    )

    #step2.py {conf_making_level} {d} {s2_norun} {u}
    sub1.add_argument(
        "-conf_making_level",
        type = int,
        default = 1,
        help = "conformer level 1: quick, 2: medium, 3: comprehensive; default: %(default)s.")

    #step3.py {c} {x} {f} {p} {r} {d} {s3_norun} {u}
    sub1.add_argument(
        "-c", metavar=('start','end'),
        type=int,
        default = [1, 99999], nargs = 2,
        help = "Starting and ending conformer; default: %(default)s."
    )
    sub1.add_argument(
        "-x", metavar = "/path/to/delphi",
        default = "delphi",
        help = "Delphi executable location; default: %(default)s."
    )
    sub1.add_argument(
        "-f", metavar = "tmp folder",
        default = "/tmp",
        help = "Delphi temporary folder; default: %(default)s."
    )
    sub1.add_argument(
        "-p", metavar = "processes",
        type = int,
        default = 1,
        help="Number of processes to use; default: %(default)s."
    )
    #should be --r:
    sub1.add_argument(
        "-r",
        default = False,
        help = "Refresh opp files and head3.lst without running Delphi",
        action = "store_true"
    )

    #step4.py --xts {titr_type} {i} {interval} {n} {ms} {s4_norun} {u}
    sub1.add_argument(
        "-titr_type", metavar="ph or eh",
        type = str,
        default = "ph",
        help = "Titration type, pH or Eh; default: %(default)s."
    )
    sub1.add_argument(
        "-i",
        metavar = "initial ph/eh",
        type = float,
        default = 0.0,
        help="Initial pH/Eh of titration; default: %(default)s."
    )
    sub1.add_argument(
        "-interval", metavar="interval",
        type = float,
        default = 1.0,
        help = "Titration interval in pJ or mV; default: %(default)s."
    )
    sub1.add_argument(
        "-n", metavar = "steps",
        type = int,
        default = 15,
        help = "number of steps of titration; default: %(default)s."
    )
    sub1.add_argument(
        "--ms",
        default = False,
        help = "Enable microstate output",
        action="store_true"
    )
    sub1.set_defaults(func=bench_script_setup)

    # launch_batch
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
        "-n_active",
        type = int,
        default = N_ACTIVE,
        help = """The number of jobs to keep launching; default: %(default)s.
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
    #TODO?
    #sub3.add_argument(
    #    "--do_not_schedule",
    #    default = False,
    #    help = "Do not schedule via crontab. Use for very small jobs, i.e. number of pdbs < N_ACTIVE.",
    #    action="store_true"
    #)
    sub2.set_defaults(func=bench_launch_batch)

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
