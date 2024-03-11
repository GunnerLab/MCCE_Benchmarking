#!/usr/bin/env python

"""
Module: cli.py

Command line interface for MCCE benchmarking.
Main entry point: "bench_setup"

Then 3 sub-commands:
 1. "pkdb_pdbs"
    Sub-command for setting up <bench_dir>/RUNS folder
    using the pdbs in pKaDBv1 & job_name_run.sh script.
 2. "user_pdbs"
    Sub-command for setting up <bench_dir>/RUNS folder
    using the user's pdbs & job_name_run.sh script. 
 3. "launch"
    Sub-command for launching a batch of jobs.
    Can be by-passed if 1. or 2. have the --launch flag
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
# import class of files resources and constants:
from mcce_benchmark import BENCH, LOG_HDR, ENTRY_POINTS, SUB1, SUB2, SUB3
from mcce_benchmark import RUNS_DIR, N_BATCH, N_PDBS
from mcce_benchmark.io_utils import Pathok, subprocess_run
from mcce_benchmark import audit, job_setup, batch_submit, scheduling, custom_sh
from IPython.core.formatters import format_display_data
import logging
from pathlib import Path
import subprocess
import sys
from time import sleep
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

info_fh = Path("benchmark.info")
if not info_fh.exists():
    with open(info_fh, "w") as fh:
        fh.writelines(LOG_HDR)
#.......................................................................


CLI_NAME = ENTRY_POINTS["setup"] # as per pyproject.toml entry point

bench_default_jobname = BENCH.DEFAULT_JOB

HELP_1 = f"""
Sub-command for setting up <bench_dir>/RUNS folder & job_name_run.sh script, e.g.:
>{CLI_NAME} {SUB1} -bench_dir <folder name>
"""

HELP_2 = f"""
Sub-command for setting up <bench_dir>/RUNS folder using user's pdb_list
& job_name_run.sh script, e.g.:
>{CLI_NAME} {SUB2} -bench_dir <folder name>
"""

HELP_3 = f"""Sub-command for launching the automated scheduling of runs in batches; e.g.:
>{CLI_NAME} {SUB3} -bench_dir <folder name> -n_batch 15
Note: if provided, the value for the -job_name option must match the one used in `setup_job`.
"""

DESC = f"""
Description:
Launch a MCCE benchmarking job using either the curated structures from the pKaDBv1
or the user's pdbs list.

The main command is {CLI_NAME} along with one of 2 sub-commands:
- Sub-command 1: {SUB1}: setup the dataset and run script to run mcce steps 1 through 4;
- Sub-command 2: {SUB2}: setup the user dataset and run script to run mcce steps 1 through 4;
- Sub-command 3: {SUB3}: launch the automated scheduling of runs in batchs ;
"""

EPI = f"""
Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues
"""

USAGE = f"""
{CLI_NAME} <+ 1 sub-command: {SUB1} or {SUB2} or {SUB3} > <related args>\n
Examples:
1. {SUB1}: Data & script setup using pkDBv1 pdbs:
   - Minimal input: value for -bench_dir option:
     >{CLI_NAME} {SUB1} -bench_dir <folder path>

   - Using non-default option(s) (then job_name is required!):
     >{CLI_NAME} {SUB1} -bench_dir <folder path> -d 8 -job_name <job_e8>

2. {SUB2}: Data & script setup using user's pdb list:
   - Minimal input: value for -bench_dir option, -pdb_list:
     >{CLI_NAME} {SUB2} -bench_dir <folder path> -pdb_list <path to dir with pdb files OR file listing pdbs paths>

   - Using non-default option(s) (then job_name is required! ):
     >{CLI_NAME} {SUB2} -bench_dir <folder path> -pdb_list <path> -d 8 -job_name <job_e8>

3. {SUB3}: Launch runs:
   - Minimal input: value for -bench_dir option: IFF no non-default job_name & sentinel_file were passed in {SUB1}
     >{CLI_NAME} {SUB3} -bench_dir <folder path>

   - Using non-default option(s):
     >{CLI_NAME} {SUB3} -bench_dir <folder path> -n_batch <jobs to maintain>
    Note: if changing the default sentinel_file="pk.out" to, e.g. step2_out.pdb,
        then the 'norun' script parameters for step 3 & 4 must be set accordingly:
        >{CLI_NAME} {SUB3} -bench_dir <folder path> -sentinel_file step2_out.pdb --s3_norun --s4_norun

"""


def args_to_str(args:argNamespace) -> str:
    """Return cli args to string.
    Note: Using format_display_data to obtain output
    as in a notebookk where the 'func' object ref is
    in readeable form instead of uid.
    """

    return f"{CLI_NAME} args:\n{format_display_data(vars(args))[0]['text/plain']}\n"


def log_mcce_version(pdbs_dir:str) -> None:
    """MCCE version(s) from run.log files."""

    pdbs_fp = Pathok(pdbs_dir, raise_err=False)
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


def bench_job_setup(args:argNamespace) -> None:
    """Benchmark cli function for sub-commands 1 and 2.
    Processing steps:
     - Create args.bench_dir/RUNS folders.
     - Write fresh book file
     - Write script for args.job_name
     - Delete all previous sentinel files, if any
    """

    in_benchmarks = Path.cwd().name == args.bench_dir.name
    if in_benchmarks:
        args.bench_dir = Path.cwd()

    if not args.bench_dir.exists():
        args.bench_dir.mkdir()

    logger.info(args_to_str(args))

    if "pdbs_list" in args:
        job_setup.setup_user_runs(args)
    else:
        job_setup.setup_expl_runs(args.bench_dir,
                                  args.n_pdbs)

    # determine if args are all defaults
    use_default_sh = custom_sh.all_opts_are_defaults(args)
    if use_default_sh:
        job_setup.write_default_run_script(args.bench_dir, args.job_name)
    else:
        custom_sh.write_run_script_from_template(args.bench_dir,
                                                 args.job_name,
                                                 job_args = args)

    job_setup.delete_sentinel(args.bench_dir, args.sentinel_file)
    logger.info("Setup over.")

    if args.launch:
        logger.info("Doing scheduling as per --launch")
        scheduling.schedule_job(args)

        # read run.log files for version(s):
        log_mcce_version(args.bench_dir.joinpath(RUNS_DIR))

    return


def bench_launch_batch(args:argNamespace) -> None:
    """Benchmark cli function for 'launch' sub-command.
    PRE-REQS:
    args.bench_dir & subfolders, and script for args.job_name exist
    as previously created via 'bench_setup' command.
    """

    in_benchmarks = Path.cwd().name == args.bench_dir.name
    if in_benchmarks:
        args.bench_dir = Path.cwd()

    logger.info(args_to_str(args))
    args.bench_dir = Pathok(args.bench_dir)

    #log script text again in case it was manualy modified.
    sh_name = f"{args.job_name}.sh"
    sh_path = Pathok(args.bench_dir.joinpath(RUNS_DIR, sh_name))
    sh_msg = ("Script contents prior to launch:\n```\n"
              + f"{job_setup.get_script_contents(sh_path)}\n```\n"
             )
    logger.info(sh_msg)

    scheduling.schedule_job(args)

    # finally, read run.log files for version(s):
    log_mcce_version(args.bench_dir.joinpath(RUNS_DIR))

    return


def bench_parser():
    """Command line arguments parser with sub-commands for use in benchmarking."""

    def arg_valid_dirpath(p: str) -> Union[None, Path]:
        """Return resolved path from the command line."""
        if not len(p):
            return None
        return Path(p).resolve()

    def arg_valid_dir_or_file(p: str) -> Union[None, Path]:
        """Check if resolved path points to a dir or file."""
        if not len(p):
            return None
        pr = Path(p).resolve()
        if pr.is_dir():
            if len(list(pr.glob("*.pdb"))) == 0:
                logger.error(f"No pdbs in folder: {pr}.")
                raise ValueError(f"No pdbs in folder: {pr}.")
            return pr
        if pr.is_file() and pr.exists():
            return pr
        else:
            return None

    def arg_valid_npdbs(n_pdbs: str) -> int:
        """Return validated number or 1."""
        try:
            n = abs(int(n_pdbs))
            if 0 < n <= N_PDBS:
                return n
            else:
                logger.warning(f"{n_pdbs= } not in (1, {N_PDBS}): reset to 1")
                return 1
        except ValueError:
            logger.warning(f"{n_pdbs= } not in (1, {N_PDBS}): reset to 1")
            return 1


    # parent parser
    p = ArgumentParser(
        prog = f"{CLI_NAME} ",
        description = DESC,
        usage = USAGE,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = EPI,
    )

    # common_parser: for pkdb_pdbs and user_pdbs subs
    cp = ArgumentParser(add_help=False)

    cp.add_argument(
        "-job_name",
        type = str,
        default = bench_default_jobname,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'bench_dir' that launches the MCCE simulation
        in 'bench_dir'/RUNS_DIR subfolders; default: %(default)s.
        """
    )
    # sentinel_file (e.g. pK.out) is part of script setup to ensure it is deleted prior to using launch sub-command.
    cp.add_argument(
        "-sentinel_file",
        type = str,
        default = "pK.out",
        help = """File whose existence signals a completed step; When running all 4 MCCE steps (default),
        this file is 'pK.out', while when running only the first 2 [future implementation], this file is 'step2_out.pdb'; default: %(default)s.
        """
    )
    #step1.py prot.pdb {wet} {noter} {d} {s1_norun} {u}
    cp.add_argument(
        "-wet",
        type = bool,
        default = False,
        help = "Keep water molecules.",
    )
    cp.add_argument(
        "--noter",
        default = False,
        help = "Do not label terminal residues (for making ftpl).", action="store_true"
    )
    # common to all steps:
    cp.add_argument(
        "-u", metavar = "Key=Value",
        type = str, default = "",
        help = """
        User selected, comma-separated KEY=var pairs from run.prm; e.g.:
        -u HOME_MCCE=/path/to/mcce_home,H2O_SASCUTOFF=0.05,EXTRA=./extra.tpl; default: %(default)s.
        Note: No space after a comma!"""
    )
    # norun option for each steps:
    cp.add_argument(
        "-s1_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 1."
    )
    cp.add_argument(
        "-s2_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 2."
    )
    cp.add_argument(
        "-s3_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 3."
    )
    cp.add_argument(
        "-s4_norun",
        default = False,
        type = bool,
        help = "Create run.prm without running step 4."
    )
    # steps 1-3:
    cp.add_argument(
        "-d", metavar = "epsilon",
        type = float,
        default = 4.0,
        help = "protein dielectric constant for delphi; %(default)s."
    )
    #step2.py {conf_making_level} {d} {s2_norun} {u}
    cp.add_argument(
        "-conf_making_level",
        type = int,
        default = 1,
        help = "conformer level 1: quick, 2: medium, 3: comprehensive; default: %(default)s.")
    #step3.py {c} {x} {f} {p} {r} {d} {s3_norun} {u}
    cp.add_argument(
        "-c", metavar=('start','end'),
        type=int,
        default = [1, 99999], nargs = 2,
        help = "Starting and ending conformer; default: %(default)s."
    )
    cp.add_argument(
        "-x", metavar = "/path/to/delphi",
        default = "delphi",
        help = "Delphi executable location; default: %(default)s."
    )
    cp.add_argument(
        "-f", metavar = "tmp folder",
        default = "/tmp",
        help = "Delphi temporary folder; default: %(default)s."
    )
    cp.add_argument(
        "-p", metavar = "processes",
        type = int,
        default = 1,
        help="Number of processes to use; default: %(default)s."
    )
    #should be --r in step3.py:
    cp.add_argument(
        "-r",
        default = False,
        help = "Refresh opp files and head3.lst without running Delphi",
        action = "store_true"
    )
    #step4.py --xts {titr_type} {i} {interval} {n} {ms} {s4_norun} {u}
    cp.add_argument(
        "-titr_type", metavar="ph or eh",
        type = str,
        default = "ph",
        help = "Titration type, pH or Eh; default: %(default)s."
    )
    cp.add_argument(
        "-i",
        metavar = "initial ph/eh",
        type = float,
        default = 0.0,
        help="Initial pH/Eh of titration; default: %(default)s."
    )
    cp.add_argument(
        "-interval", metavar="interval",
        type = float,
        default = 1.0,
        help = "Titration interval in pJ or mV; default: %(default)s."
    )
    cp.add_argument(
        "-n", metavar = "steps",
        type = int,
        default = 15,
        help = "number of steps of titration; default: %(default)s."
    )
    cp.add_argument(
        "--ms",
        default = False,
        help = "Enable microstate output",
        action = "store_true"
    )
    cp.add_argument(
        "--launch",
        default = False,
        help = "Schedule the job right away (no chance of inspecting <job_name>.sh!)",
        action="store_true"
    )

    subparsers = p.add_subparsers(required = True,
                                  title = f"{CLI_NAME} sub-commands",
                                  dest = "subparser_name",
                                  description = "Sub-commands of MCCE benchmarking cli.",
                                  help = """The 3 choices for the benchmarking process:
                                  1) Setup pkdbv1 data & run-script: {SUB1}
                                  2) Setup user data & run-script: {SUB2}
                                  3) Schedule batch runs for mcce steps 1 through 4: {SUB3}
                                  """,
                                 )

    # pkdb_pdbs
    sub1 = subparsers.add_parser(SUB1,
                                 help=HELP_1,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 parents=[cp]
                                 )
    sub1.add_argument(
        "-bench_dir",
        required = True,
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        RUNS folder reside. The directory is created if it does not exists unless this cli is
        called within that directory.
        """
    )
    sub1.add_argument(
        "-n_pdbs",
        default = 120,
        type = int,
        help = """The number of curated pdbs to setup for the benchmarking job; max=default: %(default)s.
        """
    )
    sub1.set_defaults(func=bench_job_setup)

    # user_pdbs
    sub2 = subparsers.add_parser(SUB2,
                                 help=HELP_2,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 parents=[cp]
                                 )
    sub2.add_argument(
        "-bench_dir",
        required = True,
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        RUNS folder reside. The directory is created if it does not exists unless this cli is
        called within that directory.
        """
    )
    sub2.add_argument(
        "-pdbs_list",
        type = arg_valid_dir_or_file,
        help = """The path to a dir containing pdb files OR the path to a file listing the
        pdbs file paths.
        """
    )
    sub2.set_defaults(func=bench_job_setup)

    # launch
    sub3 = subparsers.add_parser(SUB3,
                                 help=HELP_3,
                                 formatter_class = RawDescriptionHelpFormatter
                                )
    sub3.add_argument(
        "-bench_dir",
        required = True,
        type = arg_valid_dirpath,
        help = """The user's choice of directory for setting up the benchmarking job(s); this is where the
        RUNS folder reside. The directory is created if it does not exists unless this cli is
        called within that directory.
        """
    )
    sub3.add_argument(
        "-job_name",
        type = str,
        default = bench_default_jobname,
        help = """The descriptive name, devoid of spaces, for the current job (don't make it too long!); required.
        This job_name is used to identify the shell script in 'bench_dir' that launches the MCCE simulation
        in 'bench_dir'/RUNS_DIR subfolders; default: %(default)s.
        """
    )
    sub3.add_argument(
        "-n_batch",
        type = int,
        default = N_BATCH,
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
    Command line interface for MCCE benchmarking entry point 'bench_expl_pkas'.
    """

    cli_parser = bench_parser()
    args = cli_parser.parse_args(argv)
    args.func(args)

    return


if __name__ == "__main__":

    bench_cli(sys.argv[:1])
