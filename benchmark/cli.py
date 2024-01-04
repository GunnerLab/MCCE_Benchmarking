# WIP - copied from other project

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import sys
import time
from typing import Union, TextIO


# TODO:
# Implement logging

# 1. ID cli parameters
# 2. main fns:
#    setup_bench_dir
#    launch_batch



###############################################################


def clear_folder(dir_path: str, file_type:str = None,
                 del_subdir:bool=False,
                subdir_startswith = "CDC_") -> None:
    """Delete all files in folder."""

    p = Path(dir_path)
    if not p.is_dir():
        # no folder, nothing to clear
        return

    if file_type is None:
        for f in p.iterdir():
            if not f.is_dir():
                f.unlink()
            else:
                if (del_subdir
                    and f.name.startswith(subdir_startswith)):
                    delete_folder(f)
    else:
        if file_type.startswith("."):
            fname = f"*{file_type}"
        else:
            fname = f"*.{file_type}"

        for f in p.glob(fname):
            f.unlink()
    return


def delete_folder(dir_path: str) -> None:
    """Delete folder and all files there in."""

    p = Path(dir_path)
    if not p.is_dir():
        return
    shutil.rmtree(str(p))

    return


def save_dict_to_txt(dict_data: dict, text_filepath: str) -> None:
    """
    Save a dict to a text file.
    Extracted from unused /structure.DynamicStructure and modified.
    """
    text_filepath = Path(text_filepath)
    if not text_filepath.suffixes:
        text_filepath = text_filepath + ".txt"

    with open(text_filepath, "w") as out:
        for k, v in dict_data.items():
            out.write(f"{k} : {v}\n")

    return


#.......................................................................
CLI_NAME = "bench"  # as per pyproject.toml


USAGE = f"{CLI_NAME} <sub-command for step to run> <args for step>\n"

DESC = """
    MCCE Benchmarking CLI.

    The main command for benchmarking MCCE is `bench`, which expects a sub-command,
    one among `from_step1`, `from_step3`, then the argument(s) for each.

    WARNING: Only the `from_step1` subcommand is currently (or soon to be) implemented
"""

HELP_1 = f"""
    from_step1: Run all first 4 mcce steps from step 1.
    ------
    * Minimal number of arguments, 2: mcce dir and sample size
    * Commands: {CLI_NAME} step1 <step 1 args>
    * Example:
    {CLI_NAME} step1 /path/to/mcce 3

    * All other args have their default values:
     -msout_file: "pH7eH0ms.txt"
     -sampling_kind: deterministic
     -seed: None

"""
HELP_2 = f"""
    from_step3: Run mcce steps 3 and 4. Use when a reference step2_out.pdb exists
    for each pdb in PDBS subfolders.
    ------
    * Minimal number of arguments, 1: mcce dir
    * Commands: {CLI_NAME} step2 <step 2 args>
    * Example:
    {CLI_NAME} step2 /path/to/mcce

"""
HELP_3 = f"""
    step 3: sites energies and create ms matrices
    ------
    * Minimal number of arguments, 1: mcce dir
    * Commands: {CLI_NAME} step3 <step 3 args>
    * Example:
    {CLI_NAME} step3 /path/to/mcce

    * All other args have their default values:
     - cofactors_list: ["CLA","CLB","BCR","SQD","HOH","MEM"]

"""


def do_ms_to_pdbs(args):
    "args: cli args for step1"
    return


def do_convert_pdbs(args):
    "args: cli args for step2"
    return


def do_site_energies(args):
    "args: cli args for step3"
    return


def bench_parser():
    """Command line arguments parser with sub-commands defining the main choices of actions
    in the MCCE benchmarking process.
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
    subparsers = p.add_subparsers(required=True,
                                  title="Benchmark actions commands",
                                  description="Subcommands for MCCE benchmarking MCCE.',
                                  help="""The 2 ways of running a benchmarking job:
                                  from step1, or from step3 (not yet implemented).""",
                                  dest="subparser_name"
                                 )

##### TODO ####################################
    # do_ms_to_pdbs
    step1 = subparsers.add_parser('step1',
                                  formatter_class = RawDescriptionHelpFormatter,
                                  help=HELP_1)
    step1.add_argument(
        "mcce_dir",
        type = arg_valid_dirpath,
        help = "The folder with files from a MCCE simulation; required.",
    )
    step1.add_argument(
        "sample_size",
        type = int,
        help = "The size of the microstates sample, hence the number of pdb files to write; required",
    )
    step1.add_argument(
        "-msout_file",
        type = str,
        default = "pH7eH0ms.txt",
        help = "Name of the mcce_dir/ms_out/ microstates file, `pHXeHYms.txt'; default: %(default)s.""",
    )
    step1.add_argument(
        "-sampling_kind",
        type = str,
        choices = ["d", "deterministic", "r", "random"],
        default = "r",
        help = """The sampling kind: 'deterministic': regularly spaced samples,
        'random': random indices over the microstates space; default: %(default)s.""",
    )
    step1.add_argument(
        "-seed",
        type = int,
        default = None,
        help = "The seed for random number generation. Only applies to random sampling; default: %(default)s.",
    )
    step1.set_defaults(func=do_ms_to_pdbs)

    # do_convert_pdbs
    step2 = subparsers.add_parser('step2',
                                  formatter_class = RawDescriptionHelpFormatter,
                                  help=HELP_2)
    step2.add_argument(
        "mcce_dir",
        type = arg_valid_dirpath,
        help = "The folder with files from a MCCE simulation; required.",
    )
    step2.add_argument(
        "-empty_parsed_dir",
        type = bool,
        default = True,
        # folder reuse:
        help = "If True, the pdb files in the folder `parsed_dir` will be deleted before the new conversion."
    )
    step2.set_defaults(func=do_convert_pdbs)

    # do_site_energies + matrices
    step3 = subparsers.add_parser('step3',
                                  formatter_class = RawDescriptionHelpFormatter,
                                  help=HELP_3)
    step3.add_argument(
        "mcce_dir",
        type = arg_valid_dirpath,
        help = "The folder with files from a MCCE simulation; required.",
    )
    # Remove? Current cofactor of interest is "CLA" (hard-coded in `microstates_sites_energies`).
    step3.add_argument(
        "-cofactor_list",
        type = list,
        default = cofactors_list,
        help="List of cofactors (3-char string) found in the pdb used in the MCC simulation; default: %(default)s.",
    )
    step3.set_defaults(func=do_site_energies)

    return p


def pipeline_cli(argv=None):
    """
    Command line interface to:
    - create a collection of pdb files from a mcce microstates sample.
    - convert the pdbs to gromacs format
    - create the sampled microstates matrix or matrices
    - calculate the site energy for CLA cofactor.
    """

    cli_parser = pipeline_parser()
    args = cli_parser.parse_args(argv)
    #if argv is None:
    #    cli_parser.print_help()
    #    return
    args.func(args)

    return


if __name__ == "__main__":
    pipeline_cli(sys.argv[1:])
