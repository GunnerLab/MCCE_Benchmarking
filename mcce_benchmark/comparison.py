#!/usr/bin/env python

"""
Cli end point for comparison of two sets of runs. `compare`

Cli parser with options:
  -dir1: path to run set 1
  -dir2: path to run set 2
  --pkdb_pdbs: Flag enabling the creation of the analysis output files
               in each of the sets if analysis folder not found.
               Thus, this switch enables the by-passing of the
               bench_analyze <sub-command> step.
  --dir2_is_refset: Flag presence indicate dir2 holds the NAME of a reference dataset, 
               currently 'parse.e4' for pH titrations.
"""


from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
from mcce_benchmark import BENCH, ENTRY_POINTS, SUB1, SUB2
from mcce_benchmark import OUT_FILES, ANALYZE_DIR, RUNS_DIR
from mcce_benchmark import analysis, diff_mc, mcce_env, plots

from mcce_benchmark.io_utils import Pathok, subprocess_run
from mcce_benchmark.io_utils import get_book_dirs_for_status, load_tsv, fout_df, pk_to_float
from mcce_benchmark.io_utils import dict_to_json, json_to_dict
import subprocess
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#................................................................................
def compare_runs(args:argNamespace):

    kind = SUB1 if args.pkdb_pdbs else SUB2

    analyze1 = args.dir1.joinpath(ANALYZE_DIR)
    if not analyze1.exists():
        analysis.analyze_runs(args.dir1, kind)

    analyze2 = args.dir2.joinpath(ANALYZE_DIR)
    if not analyze2.exists():
        analysis.analyze_runs(args.dir2, kind)

    out_dir = Path(args.o)

    # 0. validate
    mcce_env.validate_envs(args.dir1, args.dir2, subcmd=kind,
                           dir2_is_refset=args.dir2_is_refset)

    # 1. get collated sum_crg.out diff:
    sc1 = analyze1.joinpath(OUT_FILES.ALL_SUMCRG.value)
    sc2 = analyze2.joinpath(OUT_FILES.ALL_SUMCRG.value)
    tsv_fp = out_dir.joinpath(OUT_FILES.ALL_SUMCRG_DIFF.value)
    diff_mc.get_diff(sc1, sc2, save_to_tsv=tsv_fp)


    # 2. get pkas to dict from all_pkas1, all_pkas2 & match pkas:
    d1 = json_to_dict(analyze1.joinpath(OUT_FILES.JOB_PKAS.value))
    d2 = json_to_dict(analyze2.joinpath(OUT_FILES.JOB_PKAS.value))

    matched_pkas = analysis.match_pkas(d1, d2)

    logger.info(f"Plotting residues analysis -> pic.")
    save_to = out_dir.joinpath(OUT_FILES.FIG_FIT_PER_RES.value)
    plots.plot_res_analysis(matched_pkas, save_to)

    matched_fp = out_dir.joinpath(OUT_FILES.MATCHED_PKAS.value)
    analysis.matched_pkas_to_csv(matched_fp, matched_pkas, kind=kind)

    logger.info(f"Calculating the matched pkas stats into dict.")
    outlier_fp = out_dir.joinpath(OUT_FILES.RES_OUTLIER.value)
    _ = analysis.res_outlier_count(matched_fp, save_to=outlier_fp)

    # matched_df: for matched_pkas_stats and plots.plot_pkas_fit
    matched_df = analysis.load_matched_pkas(matched_fp)
    d_stats = analysis.matched_pkas_stats(matched_df, subcmd=kind)
    print(d_stats["report"])
    json_fp = out_dir.joinpath(OUT_FILES.MATCHED_PKAS_STATS.value)
    dict_to_json(d_stats, json_fp)

    logger.info(f"Plotting pkas fit -> pic.")
    save_to = out_dir.joinpath(OUT_FILES.FIG_FIT_ALLPKS.value)
    plots.plot_pkas_fit(matched_df, d_stats, save_to)

    return


#........................................................................
CLI_NAME = ENTRY_POINTS["compare"] # as per pyproject.toml entry point

DESC = f"""
Description:
compare the pkas from two sets of mcce calculations.
Options:
  -dir1: path to run set 1
  -dir2: path to run set 2
  --pkdb_pdbs: flag enabling the creation of the analysis output files
               in each of the sets if analysis folder not found.
               Thus, this switch enables the by-passing of the
               bench_analyze <sub-command> step.

Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues
"""
USAGE = f"""
1. Without flag --pkdb_pdbs means the 2 sets were created with user_pdbs
   >{CLI_NAME} -dir1 <path to set 1> -dir2 <path to set 2>
2. With flag --pkdb_pdbs means the 2 sets were created with pkdb_pdbs_pdbs:
   >{CLI_NAME} -dir1 <path to set 1> -dir2 <path to set 2>
"""


def compare_parser():
    """Cli arguments parser for use in benchmark comparison. """

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
    )

    p.add_argument(
        "-dir1",
        required=True,
        type = arg_valid_dirpath,
        help = """Path to run set 1."""
    )
    p.add_argument(
         "-dir2",
        required=True,
        type = arg_valid_dirpath,
        help = """Path to run set 1."""
    )
    p.add_argument(
        "--pkdb_pdbs",
        default = False,
        action = "store_true",
        help = """
        Flag enabling the creation of the analysis output files
        in each of the sets if analysis folder not found.
        Thus, this switch enables the by-passing of the
        bench_analyze <sub-command> step.
        """
    )
    p.add_argument(
        "--dir2_is_refset",
        default = False,
        action = "store_true",
        help = """
        Flag presence indicate dir2 holds the NAME of a reference dataset, currently 'parse.e4'.
        """
    )

    return p


def compare_cli(argv=None):
    """
    Command line interface for MCCE benchmarking comparison entry point.
    """

    cli_parser = compare_parser()

    if argv is None or len(argv) <= 1:
        cli_parser.print_usage()
        return

    if '-h' in argv or '--help' in argv:
        cli_parser.print_help()
        return

    args = cli_parser.parse_args(argv)

    # OK to compare?
    for d in [args.dir1, args.dir2]:
        bench = Pathok(d)
        book_fp = bench.joinpath(BENCH.RUNS_DIR, BENCH.Q_BOOK)
        pct = analysis.pct_completed(book_fp)
        if pct < 1.:
            logger.info(f"Runs not 100% complete in {d}, try again later; completed = {pct:.2f}")
            return

    compare_runs(args)

    return


if __name__ == "__main__":

    compare_cli(sys.argv[1:])
