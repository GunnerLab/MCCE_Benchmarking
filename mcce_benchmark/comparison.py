#!/usr/bin/env python

"""
Cli end point for comparison of two sets of runs. `compare`

Cli parser with options:
  -dir1: path to run set 1
  -dir2: path to run set 2
  -o: path of output folder
  --pkdb_pdbs: Flag enabling the creation of the analysis output files
               in each of the sets if analysis folder not found.
               Thus, this switch enables the by-passing of the
               bench_analyze <sub-command> step.
  --dir2_is_refset: Flag presence indicate dir2 holds the NAME of a reference dataset,
               currently 'parse.e4' for pH titrations.
"""


from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace
from mcce_benchmark import BENCH, ENTRY_POINTS, SUB1, SUB2
from mcce_benchmark import OUT_FILES, ANALYZE_DIR, RUNS_DIR
from mcce_benchmark import pkanalysis, diff_mc, mcce_env, plots

from mcce_benchmark.io_utils import Pathok, subprocess_run, subprocess
from mcce_benchmark.io_utils import get_book_dirs_for_status, tsv_to_df, fout_df, pk_to_float
from mcce_benchmark.io_utils import get_sumcrg_col_specs, get_sumcrg_hdr, to_pickle, from_pickle
from mcce_benchmark.scheduling import clear_crontab
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#................................................................................
def compare_runs(args:Namespace):

    kind = SUB1 if args.pkdb_pdbs else SUB2

    analyze1 = args.dir1.joinpath(ANALYZE_DIR)
    if not analyze1.exists():
        pkanalysis.analyze_runs(args.dir1, kind)

    analyze2 = args.dir2.joinpath(ANALYZE_DIR)
    if not analyze2.exists():
        pkanalysis.analyze_runs(args.dir2, kind)

    out_dir = Path(args.o)
    if not out_dir.exists():
        out_dir.mkdir()

    logger.info(f"Validate")
    mcce_env.validate_envs(args.dir1, args.dir2, subcmd=kind,
                           dir2_is_refset=args.dir2_is_refset)

    # 1. get collated sum_crg.out diff:
    sc1 = analyze1.joinpath(OUT_FILES.ALL_SUMCRG.value)
    sc2 = analyze2.joinpath(OUT_FILES.ALL_SUMCRG.value)
    tsv_fp = out_dir.joinpath(OUT_FILES.ALL_SUMCRG_DIFF.value)
    diff_mc.get_diff(sc1, sc2, save_to_tsv=tsv_fp)


    # 2. get pkas to dict from all_pkas1, all_pkas2 & match pkas:
    d1 = from_pickle(analyze1.joinpath(OUT_FILES.JOB_PKAS.value))
    d2 = from_pickle(analyze2.joinpath(OUT_FILES.JOB_PKAS.value))

    matched_pkas = pkanalysis.match_pkas(d1, d2)

    logger.info(f"Plotting residues analysis -> pic.")
    save_to = out_dir.joinpath(OUT_FILES.FIG_FIT_PER_RES.value)
    plots.plot_res_analysis(matched_pkas, save_to)

    matched_fp = out_dir.joinpath(OUT_FILES.MATCHED_PKAS.value)
    pkanalysis.matched_pkas_to_csv(matched_fp, matched_pkas, kind=kind)

    logger.info(f"Calculating the matched pkas stats into dict.")
    outlier_fp = out_dir.joinpath(OUT_FILES.RES_OUTLIER.value)
    _ = pkanalysis.res_outlier_count(matched_fp, save_to=outlier_fp)

    # matched_df: for matched_pkas_stats and plots.plot_pkas_fit
    matched_df = pkanalysis.matched_pkas_to_df(matched_fp)
    d_stats = pkanalysis.matched_pkas_stats(matched_df, subcmd=kind)
    logger.info(d_stats["report"])
    pickle_fp = out_dir.joinpath(OUT_FILES.MATCHED_PKAS_STATS.value)
    to_pickle(d_stats, pickle_fp)

    logger.info(f"Plotting pkas fit -> pic.")
    save_to = out_dir.joinpath(OUT_FILES.FIG_FIT_ALLPKS.value)
    plots.plot_pkas_fit(matched_df, d_stats, save_to)

    return


#........................................................................
CLI_NAME = ENTRY_POINTS["compare"] # as per pyproject.toml entry point

DESC = f"""
Description:
Compare two sets of runs, ~ A/B testing
(convention: B is 'reference', whether it actually is a reference set or not, i.e.: A - B):

Options:
  -dir1: path to run set 1
  -dir2: path to run set 2
  --pkdb_pdbs: Absence means 'user_pdbs'
               Flag enabling the creation of the analysis output files
               in each of the sets if analysis folder not found.
               Thus, this switch enables the by-passing of the
               bench_analyze <sub-command> step.

  --dir2_is_refset: Flag presence indicates that dir2 value is a refset name;
                    If used, --pkdb_pdbs must also be present.

  (mce) >bench_compare -dir1 <d1> dir2 parse.e4 --pkdb_pdbs --dir2_is_refset


Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues
"""
USAGE = f""" >{CLI_NAME} -dir1 <d1> -dir2 <d2> [+ 2 flags]

1. Without flag --pkdb_pdbs means the 2 sets were created with user_pdbs
   >{CLI_NAME} -dir1 <path to set 1> -dir2 <path to set 2>

2. With flag --pkdb_pdbs means the 2 sets were created with pkdb_pdbs_pdbs:
   >{CLI_NAME} -dir1 <path to set 1> -dir2 <path to set 2>

3. With flag --dir2_is_refset: indicates that dir2 is a refset name;
   If used, --pkdb_pdbs must also be present.
   >{CLI_NAME} -dir1 <d1> dir2 parse.e4 --pkdb_pdbs --dir2_is_refset
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
        help = """Path to run set 2."""
    )
    p.add_argument(
         "-o",
        meta = "output",
        required=True,
        type = arg_valid_dirpath,
        help = """Path to comparison results."""
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
    args = cli_parser.parse_args(argv)

    # OK to compare?
    for d in [args.dir1, args.dir2]:
        bench = Pathok(d)
        book_fp = bench.joinpath(RUNS_DIR, BENCH.Q_BOOK)
        pct = pkanalysis.pct_completed(book_fp)
        if pct < 1.:
            logger.info(f"Runs not 100% complete in {d}, try again later; completed = {pct:.2f}")
            return

    clear_crontab()
    compare_runs(args)

    return


if __name__ == "__main__":

    compare_cli(sys.argv[1:])
