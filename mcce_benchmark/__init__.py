#!/usr/bin/env python

from enum import Enum
import getpass
from importlib import resources
import logging
from mcce_benchmark import _version
from pathlib import Path
import shutil
import sys
from typing import Union


#................................................................................
APP_NAME = "mcce_benchmark"

# fail fast:
USER_MCCE = shutil.which("mcce")
if USER_MCCE is None:
    raise EnvironmentError(f"{APP_NAME}, __init__ :: mcce executable not found.")


def get_user_env() -> tuple:
    """Return the sys.prefix, env name, ."""

    user_prefix = sys.prefix
    env = Path(user_prefix).name

    if "envs" not in user_prefix:
        if env != "miniconda3" and env != "anaconda3":
            logging.error("EnvironmentError: You appear not to be using conda, which is required for scheduling.")
            raise EnvironmentError("You appear not to be using conda, which is required for scheduling.")
        else:
            #logging.warning("Using base conda environment.")
            env = 'base'
    else:
         return user_prefix, env


# user envir:
USER_PRFX, USER_ENV = get_user_env()
CONDA_PATH = shutil.which("conda")

N_PDBS = 120  # UPDATE if change in dataset!

# output file names
class OUT_FILES(Enum):   # => <benchmarks_dir>/analysis/
    ALL_PKAS_FILE = "all_pkas.out"
    MATCHED_PKAS_FILE = "matched_pkas.csv"
    PKAS_STATS = "pkas_stats.csv"
    CONF_COUNTS = "conf_counts.tsv"
    RES_COUNTS = "res_counts.tsv"
    RUN_TIMES = "run_times.tsv"
    CONFS_PER_RES = "confs_per_res.tsv"
    CONFS_THRUPUT = "confs_throughput.tsv"
    CONFS_TP_PNG = "confs_throughput.png"


DEFAULT_DIR = "mcce_benchmarks"
ANALYZE_DIR = "analysis"
MCCE_EPS = 4   # default dielectric constant (epsilon) in MCCE
N_ACTIVE = 10  # number of active jobs to maintain in the process queue
ENTRY_POINTS = {"main": "bench_expl_pkas",
                "launch": "bench_launchjob",
                "analyze":"bench_analyze"}

#TODO: new needed:
#ENTRY_POINTS = {"main": "bench_expl_pkas",
#                 "launch": "bench_launchjob",
#                "mcruns": "bench_mcce_runs"
#               }

MCCE_OUTPUTS = ["acc.atm", "acc.res", "entropy.out", "extra.tpl", "fort.38",
                "head1.lst", "head2.lst", "head3.lst",
                "mc_out", "name.txt", "new.tpl", "null",
                "pK.out", "respair.lst", "rot_stat",
                "run.log", "run.prm", "run.prm.record",
                "step0_out.pdb", "step1_out.pdb",
                "step2_out.pdb", "step3_out.pdb",
                "sum_crg.out", "vdw0.lst",
               ]


def Pathok(pathname:str, check_fn:str=None, raise_err=True) -> Union[Path, bool]:
    """Return path if check passed, else raise error.
    check_fn: one of 'exists', 'is_dir', 'is_file'.
    if raise_err=False, return False insteadt of err.
    """

    pathname = Path(pathname)
    if check_fn not in ['exists', 'is_dir', 'is_file']:
        check_fn = 'exists'

    if check_fn == 'exists':
        msg = f"Path not found: {pathname}"
    elif check_fn == 'is_dir':
        msg = f"Directory not found: {pathname}"
    elif check_fn == 'is_file':
        msg = f"Path is not a file: {pathname}"

    if not pathname.__getattribute__(check_fn)():
        if not raise_err:
            return False

        logging.error(msg)
        raise FileNotFoundError(msg)

    return pathname


#TODO: add reference_runs folder
class Bench_Resources():
    """Immutable class to store package data paths and main constants."""

    __slots__ = ("_BENCH_DATA",
                 "_BENCH_DB",
                 "_BENCH_WT",
                 "_BENCH_PROTS",
                 "_CLEAN_PDBS",
                 "_BENCH_PDBS",
                 "_DEFAULT_JOB",
                 "_DEFAULT_JOB_SH",
                 "_Q_BOOK",
                 "_BENCH_Q_BOOK",
                 "_BENCH_REFS",
                 "_BENCH_PARSE_E4",
                )

    def __init__(self, res_files=resources.files(f"{APP_NAME}.data")):
        self._BENCH_DATA = res_files
        self._BENCH_DB = self._BENCH_DATA.joinpath("pkadbv1")
        self._BENCH_WT = self._BENCH_DB.joinpath("WT_pkas.csv")
        self._BENCH_PROTS = self._BENCH_DB.joinpath("proteins.tsv")
        self._CLEAN_PDBS = "clean_pdbs"
        self._BENCH_PDBS = self._BENCH_DB.joinpath(self._CLEAN_PDBS)
        self._DEFAULT_JOB = "default_run"
        self._DEFAULT_JOB_SH = self._BENCH_PDBS.joinpath(f"{self._DEFAULT_JOB}.sh")
        self._Q_BOOK = "book.txt"
        self._BENCH_Q_BOOK = self._BENCH_PDBS.joinpath(self._Q_BOOK)
        self._BENCH_REFS = self._BENCH_DATA.joinpath("refsets")
        self._BENCH_PARSE_E4 = self._BENCH_REFS.joinpath("parse.e4")

    @property
    def BENCH_DATA(self):
        return self._BENCH_DATA

    @property
    def BENCH_DB(self):
        return self._BENCH_DB

    @property
    def BENCH_REFS(self):
        return self._BENCH_REFS

    @property
    def BENCH_PARSE_E4(self):
        return self._BENCH_PARSE_E4

    @property
    def BENCH_WT(self):
        return self._BENCH_WT

    @property
    def BENCH_PROTS(self):
        return self._BENCH_PROTS

    @property
    def CLEAN_PDBS(self):
        return self._CLEAN_PDBS

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
        BENCH_REFS = {str(self.BENCH_REFS)}
        BENCH_PARSE_E4 = {str(self.BENCH_PARSE_E4)}
        BENCH_DB = {str(self.BENCH_DB)}
        BENCH_WT = {str(self.BENCH_WT)}
        BENCH_PROTS = {str(self.BENCH_PROTS)}
        BENCH_PDBS = {str(self.BENCH_PDBS)}
        DEFAULT_JOB = {str(self.DEFAULT_JOB)}
        DEFAULT_JOB_SH = {str(self.DEFAULT_JOB_SH)}
        BENCH_Q_BOOK = {str(self.BENCH_Q_BOOK)}
        CLEAN_PDBS = {str(self.CLEAN_PDBS)}
        Q_BOOK = {str(self.Q_BOOK)}
        """

BENCH = Bench_Resources()


#................................................................................
# Config for root logger: handlers at module level

USER = getpass.getuser()

DT_FMT = "%Y-%m-%d %H:%M:%S"
BODY = "[%(levelname)s]: %(name)s, %(funcName)s:\n\t%(message)s"
logging.basicConfig(level=logging.INFO,
                    format=BODY,
                    datefmt=DT_FMT
                   )

# file handler
fh = logging.FileHandler("benchmark.log")
fh.name = "fh"
fh.setLevel(logging.DEBUG)
# console handler
ch = logging.StreamHandler(sys.stdout)
ch.name = "ch"
ch.setLevel(logging.INFO)


def create_log_header():
    """
    Config logger for displaying app info;
    Log that info;
    Reset the handlers formatters that the module loggers will use.
    """

    # Logging to file & stream - note 'user' param
    HEADER = '%(asctime)s @%(user)s [%(levelname)s: %(name)s]: - %(message)s'
    # initial formatter:
    header_frmter = logging.Formatter(fmt=HEADER)
    fh.setFormatter(header_frmter)
    ch.setFormatter(header_frmter)

    logger = logging.getLogger(__name__)
    logger.addHandler(ch)
    logger.addHandler(fh)
    #logger.setLevel(logging.DEBUG)
    logger = logging.LoggerAdapter(logger,{'user':USER})

    # output start msg and app defaults:
    msg_body = f"""
        Globals: {MCCE_EPS = }; {N_ACTIVE = }
        Default resource names:
        {DEFAULT_DIR = } : default benchmarking folder name
        {BENCH.CLEAN_PDBS = } : fixed
        {BENCH.Q_BOOK = } : jobs bookkeeping file
        {BENCH.DEFAULT_JOB = } (-> {BENCH.DEFAULT_JOB}.sh script in clean_pdbs/)
        {BENCH.BENCH_PARSE_E4 = } : Current reference set
        {N_PDBS = } : number of pdbs in the dataset
        Default analysis output file names (fixed):
        {OUT_FILES.MATCHED_PKAS_FILE.name = }
        {OUT_FILES.ALL_PKAS_FILE.name = }
        {OUT_FILES.CONF_COUNTS.name = }
        {OUT_FILES.RES_COUNTS.name = }
        {OUT_FILES.RUN_TIMES.name = }
        {OUT_FILES.CONFS_PER_RES.name = }
        {OUT_FILES.CONFS_THRUPUT.name = }
        User envir: {USER_ENV = }\n{'-'*70}
    """
    msg = f"START\n{'-'*70}\nAPP VER: {_version.version_tuple}\nAPP DEFAULTS:" \
          + msg_body
    logger.info(msg)

    # reset format:
    body_frmter = logging.Formatter(fmt=BODY)
    fh.setFormatter(body_frmter)
    ch.setFormatter(body_frmter)
