#!/usr/bin/env python

from datetime import datetime
from enum import Enum
import getpass
from importlib import resources
import logging
from mcce_benchmark import _version
from pathlib import Path
import shutil
import sys


#................................................................................
APP_NAME = "mcce_benchmark"

# fail fast:
USER_MCCE = shutil.which("mcce")
if USER_MCCE is None:
    raise EnvironmentError(f"{APP_NAME}, __init__ :: mcce executable not found.")
USER_MCCE = Path(USER_MCCE).parent


def get_user_env() -> str:
    """Return the env name from sys.prefix."""

    user_prefix = sys.prefix
    env = Path(user_prefix).name

    if "envs" not in user_prefix:
        if env != "miniconda3" and env != "anaconda3":
            raise EnvironmentError("You appear not to be using conda, which is required for scheduling.")
        else:
            env = 'base'
    else:
         return env


def get_conda_paths() -> tuple:
    """Return the path to conda that is not in an env,
    which is what cron 'sees', presumably.
    Needed to build cmd 'source <conda_path>/activate <env>' in crontab.
    Try: need both bin and condabin to put in path?"""

    conda_path = Path(shutil.which("conda")).parent
    conda = str(conda_path)
    if conda_path.name == "bin":
        # done
        return conda,
    # else, assume "condabin", reset:
    return str(conda_path.parent.joinpath("bin")), conda


ENTRY_POINTS = {"setup": "bench_setup",
                "launch": "bench_batch", # used by crontab :: launch 1 batch
                "analyze": "bench_analyze",
                "compare": "bench_compare"}

# bench_setup sub-commands, also used throughout:
SUB1 = "pkdb_pdbs"
SUB2 = "user_pdbs"
SUB3 = "launch"   # :: schedule via crontab

# user envir:
USER_ENV = get_user_env()
#CONDA_PATH = Path(shutil.which("conda")).parent
CONDA_PATHS = get_conda_paths()
# full path of the launch EP:
LAUNCHJOB = shutil.which(ENTRY_POINTS["launch"])

# output file names => <benchmarks_dir>/analysis/:
class FILES(Enum):
    ALL_PKAS = "all_pkas.out"
    ALL_PKAS_TSV = "all_pkas.tsv"        # contains no oob pkas if ALL_PKAS_OOB exists
    ALL_PKAS_OOB = "all_pkas_oob.tsv"    # out of bounds pKas
    ALL_SUMCRG = "all_sumcrg.out"
    ALL_SUMCRG_DIFF = "all_smcrg_diff.tsv"
    JOB_PKAS = "job_pkas.pickle"         # pickled dict
    CONF_COUNTS = "conf_counts.tsv"
    RES_COUNTS = "res_counts.tsv"
    RUN_TIMES = "run_times.tsv"
    CONFS_PER_RES = "confs_per_res.tsv"
    CONFS_THRUPUT = "confs_throughput.tsv"
    FIG_CONFS_TP = "confs_throughput.png"
    VERSIONS = "versions.txt"
    MATCHED_PKAS = "matched_pkas.csv"
    MATCHED_PKAS_STATS = "matched_pkas_stats.pickle" # pickled dict
    PKAS_STATS = "pkas_stats.csv"
    RES_OUTLIER = "outlier_residues.tsv"
    RESID_OUTLIER = "outlier_resids.tsv"
    FIG_FIT_ALLPKS = "pkas_fit.png"
    FIG_FIT_PER_RES = "res_analysis.png"

RUNS_DIR = "RUNS"
ANALYZE_DIR = "analysis"
MCCE_EPS = 4   # default dielectric constant (epsilon) in MCCE
N_BATCH = 10   # number of jobs to maintain in the process queue
N_PDBS = 120   # UPDATE if change in packaged data!

MCCE_OUTPUTS = ["acc.atm", "acc.res", "entropy.out", "extra.tpl", "fort.38",
                "head1.lst", "head2.lst", "head3.lst",
                "mc_out", "name.txt", "new.tpl", "null",
                "pK.out", "respair.lst", "rot_stat",
                "run.log", "run.prm", "run.prm.record",
                "step0_out.pdb", "step1_out.pdb",
                "step2_out.pdb", "step3_out.pdb",
                "sum_crg.out", "vdw0.lst",
               ]


class Bench_Resources():
    """Immutable class to store package data paths and main constants."""

    __slots__ = ("_BENCH_DATA",
                 "_BENCH_DB",
                 "_BENCH_WT",
                 "_BENCH_PROTS",
                 "_BENCH_PDBS",
                 "_DEFAULT_JOB",
                 "_DEFAULT_JOB_SH",
                 "_Q_BOOK",
                 "_BENCH_Q_BOOK",
                 "_BENCH_PH_REFS",
                 "_BENCH_PARSE_PHE4",
                )

    def __init__(self, res_files=resources.files(f"{APP_NAME}.data")):
        self._BENCH_DATA = res_files
        self._BENCH_DB = self._BENCH_DATA.joinpath("pkadbv1")
        self._BENCH_WT = self._BENCH_DB.joinpath("WT_pkas.csv")
        self._BENCH_PROTS = self._BENCH_DB.joinpath("proteins.tsv")
        self._BENCH_PDBS = self._BENCH_DB.joinpath(RUNS_DIR)
        self._DEFAULT_JOB = "default_run"
        self._DEFAULT_JOB_SH = self._BENCH_PDBS.joinpath(f"{self._DEFAULT_JOB}.sh")
        self._Q_BOOK = "book.txt"
        self._BENCH_Q_BOOK = self._BENCH_PDBS.joinpath(self._Q_BOOK)
        self._BENCH_PH_REFS = self._BENCH_DB.joinpath("refsets")
        self._BENCH_PARSE_PHE4 = self._BENCH_PH_REFS.joinpath("parse.e4")

    @property
    def BENCH_DATA(self):
        return self._BENCH_DATA

    @property
    def BENCH_DB(self):
        return self._BENCH_DB

    @property
    def BENCH_PH_REFS(self):
        return self._BENCH_PH_REFS

    @property
    def BENCH_PARSE_PHE4(self):
        return self._BENCH_PARSE_PHE4

    @property
    def BENCH_WT(self):
        return self._BENCH_WT

    @property
    def BENCH_PROTS(self):
        return self._BENCH_PROTS

    @property
    def BENCH_PDBS(self):
        return self._BENCH_PDBS

    @property
    def Q_BOOK(self):
        return self._Q_BOOK

    @property
    def BENCH_Q_BOOK(self):
        return self._BENCH_Q_BOOK

    @property
    def DEFAULT_JOB(self):
        return self._DEFAULT_JOB

    @property
    def DEFAULT_JOB_SH(self):
        return self._DEFAULT_JOB_SH

    def __str__(self):
        return f"""
        BENCH_DATA = {str(self.BENCH_DATA)}
        BENCH_PH_REFS = {str(self.BENCH_PH_REFS)}
        BENCH_PARSE_PHE4 = {str(self.BENCH_PARSE_PHE4)}
        BENCH_DB = {str(self.BENCH_DB)}
        BENCH_WT = {str(self.BENCH_WT)}
        BENCH_PROTS = {str(self.BENCH_PROTS)}
        BENCH_PDBS = {str(self.BENCH_PDBS)}
        DEFAULT_JOB = {str(self.DEFAULT_JOB)}
        DEFAULT_JOB_SH = {str(self.DEFAULT_JOB_SH)}
        BENCH_Q_BOOK = {str(self.BENCH_Q_BOOK)}
        Q_BOOK = {str(self.Q_BOOK)}
        """


BENCH = Bench_Resources()


#................................................................................
# Config for root logger:
DT_FMT = "%Y-%m-%d %H:%M:%S"
BODY = "[%(levelname)s]: %(name)s, %(funcName)s:\n\t%(message)s"
logging.basicConfig(level=logging.INFO,
                    format=BODY,
                    datefmt=DT_FMT,
                    filename="benchmark.log",
                    encoding='utf-8',
                   )
#................................................................................


USER = getpass.getuser()
now = datetime.now().strftime(format=DT_FMT)

LOG_HDR = f"""
START\n{'-'*70}\n{now} - {USER = } - User envir: {USER_ENV}
APP VER: {_version.version_tuple}\nAPP DEFAULTS:
Globals:
{MCCE_EPS = }; {N_BATCH = }
{N_PDBS = } : number of pdbs in the dataset

Default analysis output file names (fixed):
  ALL_PKAS: {FILES.ALL_PKAS.value}
  ALL_SUMCRG: {FILES.ALL_SUMCRG.value}
  ALL_SUMCRG_DIFF: {FILES.ALL_SUMCRG_DIFF.value}
  ALL_PKAS_OOB: {FILES.ALL_PKAS_OOB.value}
  JOB_PKAS: {FILES.JOB_PKAS.value}
  CONF_COUNTS: {FILES.CONF_COUNTS.value}
  RES_COUNTS: {FILES.RES_COUNTS.value}
  RUN_TIMES: {FILES.RUN_TIMES.value}
  CONFS_PER_RES: {FILES.CONFS_PER_RES.value}
  CONFS_THRUPUT: {FILES.CONFS_THRUPUT.value}
  FIG_CONFS_TP: {FILES.FIG_CONFS_TP.value}
  VERSIONS: {FILES.VERSIONS.value}
Additionally, with with SUB1:
  MATCHED_PKAS: {FILES.MATCHED_PKAS.value}
  MATCHED_PKAS_STATS: {FILES.MATCHED_PKAS_STATS.value}
  RES_OUTLIER = {FILES.RES_OUTLIER.value}
  RESID_OUTLIER = {FILES.RESID_OUTLIER.value}
  FIG_FIT_ALLPKS = {FILES.FIG_FIT_ALLPKS .value}
  FIG_FIT_PER_RES = {FILES.FIG_FIT_PER_RES.value}
\n{'-'*70}
"""
