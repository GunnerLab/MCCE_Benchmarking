#!/usr/bin/env python

import getpass
from importlib import resources
import logging
from mcce_benchmark import _version
from pathlib import Path
import sys


#................................................................................
APP_NAME = "mcce_benchmark"
DEFAULT_DIR = "mcce_benchmarks"
MCCE_EPS = 4   # default dielectric constant (epsilon) in MCCE
N_SLEEP = 10   # default sleep duration after last step is submitted in the job run script
N_ACTIVE = 10  # number of active jobs to maintain
ENTRY_POINTS = {"parent": "mccebench",
                "child": "mccebench_launchjob"}
CRON_COMMENT = f"Scheduled from {ENTRY_POINTS['parent']}"
MCCE_OUTPUTS = ["acc.atm", "acc.res", "entropy.out", "fort.38",
                "head1.lst", "head2.lst", "head3.lst",
                "mc_out", "name.txt", "new.tpl",
                "pK.out", "respair.lst", "rot_stat",
                "run.log", "run.prm", "run.prm.record",
                "step0_out.pdb", "step1_out.pdb",
                "step2_out.pdb", "step3_out.pdb",
                "sum_crg.out", "vdw0.lst",
               ]
USER = getpass.getuser()

class Bench_Resources():
    """Immutable class to store package data paths and main constants."""

    __slots__ = ("_BENCH_DATA",
                 "_BENCH_WT",
                 "_BENCH_PROTS",
                 "_CLEAN_PDBS",
                 "_BENCH_PDBS",
                 "_DEFAULT_JOB",
                 "_DEFAULT_JOB_SH",
                 "_Q_BOOK",
                 "_BENCH_Q_BOOK",
                )

    def __init__(self, res_files=resources.files(f"{APP_NAME}.data")):
        self._BENCH_DATA = res_files
        self._BENCH_WT = self._BENCH_DATA.joinpath("WT_pkas.csv")
        self._BENCH_PROTS = self._BENCH_DATA.joinpath("proteins.tsv")
        self._CLEAN_PDBS = "clean_pdbs"
        self._BENCH_PDBS = self._BENCH_DATA.joinpath(self._CLEAN_PDBS)
        self._DEFAULT_JOB = "default_run"
        self._DEFAULT_JOB_SH = self._BENCH_PDBS.joinpath(f"{self._DEFAULT_JOB}.sh")
        self._Q_BOOK = "book.txt"
        self._BENCH_Q_BOOK = self._BENCH_PDBS.joinpath(self._Q_BOOK)

    @property
    def BENCH_DATA(self):
        return self._BENCH_DATA

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
# Logging to file & stream
HEADER = '%(asctime)s @%(user)s [%(levelname)s: %(name)s]: - %(message)s'
BODY = "[%(levelname)s]: %(name)s, %(funcName)s:\n\t%(message)s"
# initial formatter:
header_frmter = logging.Formatter(fmt=HEADER)

# file handler
fh = logging.FileHandler("benchmark.log")
fh.name = "fh"
fh.setLevel(logging.DEBUG)
fh.setFormatter(header_frmter)

# console handler
ch = logging.StreamHandler(sys.stdout)
ch.name = "ch"
ch.setLevel(logging.INFO)
ch.setFormatter(header_frmter)

logging.basicConfig(level=logging.INFO,
                    format=BODY,
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[ch, fh]
                   )

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = logging.LoggerAdapter(logger,{'user':USER})

# output start msg and app defaults:
msg_body = f"""
    Globals: {MCCE_EPS = }; {N_SLEEP = }; {N_ACTIVE = }
    Default names:
    {DEFAULT_DIR = }
    {BENCH.CLEAN_PDBS = }
    {BENCH.Q_BOOK = }
    {BENCH.DEFAULT_JOB = }
{'-'*70}
"""
msg = f"START\n{'-'*70}\nAPP VER: {_version.version_tuple}\nAPP DEFAULTS:" \
      + msg_body
logger.info(msg)

# reset format:
body_frmter = logging.Formatter(fmt=BODY)
fh.setFormatter(body_frmter)
ch.setFormatter(body_frmter)
del logger

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
