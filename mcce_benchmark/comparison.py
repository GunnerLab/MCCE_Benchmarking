#!/usr/bin/env python

"""
Cli end point for comparison of two sets of runs. `compare`

Cli parser with options:
  -dir1: path to run set 1
  -dir2: path to run set 2
  -o: path of output folder
  --user_pdbs: Absence means 'pkdb_pdbs'
               Flag enabling the creation of the analysis output files
               in each of the sets if analysis folder not found.
               Thus, this switch enables by-passing the 'intra set'
               analysis files generation using `bench_analyze <sub-command>`.
  --dir2_is_refset: Flag presence indicate dir2 holds the NAME of a reference dataset,
               currently 'parse.e4' for pH titrations.
  The flags are mutually exclusive.
"""


from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace
from mcce_benchmark import BENCH, ENTRY_POINTS, SUB1, SUB2
from mcce_benchmark import OUT_FILES, ANALYZE_DIR, RUNS_DIR
from mcce_benchmark import mcce_env
from mcce_benchmark.cleanup import clear_folder
from mcce_benchmark import pkanalysis, diff_mc, plots
from mcce_benchmark.io_utils import Pathok, subprocess_run, subprocess
from mcce_benchmark.io_utils import get_book_dirs_for_status, tsv_to_df, fout_df, pk_to_float
from mcce_benchmark.io_utils import get_sumcrg_col_specs, get_sumcrg_hdr, to_pickle, from_pickle
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#................................................................................

def compare_runs(args:Union[dict, Namespace]):

    if isinstance(args, dict):
        args = Namespace(**args)

    kind = SUB2 if args.user_pdbs else SUB1

    ok, msg = mcce_env.validate_envs(args.dir1,
                                      args.dir2,
                                      subcmd=kind,
                                      dir2_is_refset=args.dir2_is_refset
                                      )
    if not ok:
        logger.error(f"Runs failed validation:\n{msg}")
        raise TypeError(f"Runs failed validation:\n{msg}")
    if ok and msg != "OK":
        logger.warning(f"Runs validation warning:\n{msg}")

    analyze1 = args.dir1.joinpath(ANALYZE_DIR)
    if not analyze1.exists():
        pkanalysis.analyze_runs(args.dir1, kind)

    analyze2 = args.dir2.joinpath(ANALYZE_DIR)
    if not analyze2.exists():
        pkanalysis.analyze_runs(args.dir2, kind)

    out_dir = Path(args.o)
    if not out_dir.exists():
        out_dir.mkdir()
    else:
        clear_folder(out_dir)
        logger.info(f"Cleared comparison output folder: {out_dir}")


    # 1. get collated sum_crg.out diff:
    logger.info(f"Calculating sum_crg diff file.")

    sc1 = analyze1.joinpath(OUT_FILES.ALL_SUMCRG.value)
    sc2 = analyze2.joinpath(OUT_FILES.ALL_SUMCRG.value)
    tsv_fp = out_dir.joinpath(OUT_FILES.ALL_SUMCRG_DIFF.value)

    diff_mc.get_diff(sc1, sc2, save_to_tsv=tsv_fp)

    # 2. get pkas to dict from all_pkas1, all_pkas2 & match pkas:
    logger.info(f"Matching the pkas and saving list to csv file.")

    d1 = from_pickle(analyze1.joinpath(OUT_FILES.JOB_PKAS.value))
    d2 = from_pickle(analyze2.joinpath(OUT_FILES.JOB_PKAS.value))

    matched_pkas = pkanalysis.match_pkas(d1, d2)
    matched_fp = out_dir.joinpath(OUT_FILES.MATCHED_PKAS.value)
    pkanalysis.matched_pkas_to_csv(matched_fp, matched_pkas, kind=kind)

    # 3. get figure for matched residues analysis:
    logger.info(f"Plotting matched residues analysis -> pic.")

    save_to = out_dir.joinpath(OUT_FILES.FIG_FIT_PER_RES.value)
    plots.plot_res_analysis(matched_pkas, save_to)

    # 4. matched pkas stats
    logger.info(f"Calculating the matched pkas stats into dict.")

    _ = pkanalysis.res_outlier_count(matched_fp, grp_by="res")
    _ = pkanalysis.res_outlier_count(matched_fp, grp_by="resid")

    # matched_df: for matched_pkas_stats and plots.plot_pkas_fit
    matched_df = pkanalysis.matched_pkas_to_df(matched_fp)

    d_stats = pkanalysis.matched_pkas_stats(matched_df, subcmd=kind)
    logger.info(d_stats["report"])
    # pickle the dict:
    pickle_fp = out_dir.joinpath(OUT_FILES.MATCHED_PKAS_STATS.value)
    to_pickle(d_stats, pickle_fp)

    if isinstance(d_stats["fit"], str):
        logger.info("Data could not be fitted: no plot generated.")
    else:
        logger.info(f"Plotting pkas fit -> pic.")
        save_to = out_dir.joinpath(OUT_FILES.FIG_FIT_ALLPKS.value)
        plots.plot_pkas_fit(matched_df, d_stats, save_to)

    return


#........................................................................
CLI_NAME = ENTRY_POINTS["compare"] # as per pyproject.toml entry point

DESC = f"""
Description:
Compare two sets of runs, ~ A/B testing
(convention: B is 'reference', i.e.: A - B):

Options:
  -dir1: path to run set 1
  -dir2: path to run set 2
  -o:    path to output dir
  --user_pdbs: Absence means 'pkdb_pdbs'
               Flag enabling the creation of the analysis output files
               in each of the sets if analysis folder not found.
               Thus, this switch enables by-passing the 'intra set'
               analysis files generation using `bench_analyze <sub-command>`.

  --dir2_is_refset: Flag presence indicates that dir2 value is a refset name;
               If used, --user_pdbs must NOT be present.

  (mce) >bench_compare -dir1 <d1> dir2 parse.e4 --dir2_is_refset -o ./output/dir/path


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

    # cannot have --user_pdbs & --dir2_is_refset together:
    mutex = p.add_mutually_exclusive_group()
    mutex.add_argument(
        "--user_pdbs",
        default = False,
        action = "store_true",
        help = """
        Flag enabling the creation of the analysis output files
        in each of the sets if analysis folder not found.
        Thus, this switch enables the by-passing of the
        bench_analyze <sub-command> step.
        """
    )
    mutex.add_argument(
        "--dir2_is_refset",
        default = False,
        action = "store_true",
        help = """
        Flag presence indicate dir2 holds the NAME of a reference dataset, currently 'parse.e4'.
        """)

    p.add_argument(
         "-o",
        required=True,
        type = arg_valid_dirpath,
        help = """Path to comparison results folder."""
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

    compare_runs(args)

    return


if __name__ == "__main__":

    compare_cli(sys.argv[1:])
