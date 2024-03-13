#!/usr/bin/env python

"""
Module: io_utils

Module with generic (enough) functions related to loading and saving files.

Functions:
def Pathok(pathname:str, check_fn:str=None, raise_err=True) -> Union[Path, bool]
def subprocess_run(cmd:str,
                   capture_output=True,
                   check:bool=False,
                   text=True, shell=True) -> Union[subprocess.CompletedProcess, subprocess.CalledProcessError]
def make_executable(sh_path:str) -> None:
def load_tsv(fpath:str, index_col:str=None) -> Union[pd.DataFrame, None]
def pk_to_float(value) -> float
def get_col_specs(collated:bool=False, titr_type:str='ph') -> tuple(specs, cols)
def fout_df(pko_fp:str, collated:bool=False, titr_type:str='ph') -> Union[pd.DataFrame, None]
def json_to_dict(json_fp:str) -> dict:
def dict_to_json(d:dict, json_fp:str) -> None:
"""

from mcce_benchmark import ENTRY_POINTS, OUT_FILES, ANALYZE_DIR
from mcce_benchmark.mcce_env import ENV, get_mcce_env_dir
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import subprocess
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
#......................................................................


def Pathok(pathname:str, check_fn:str=None, raise_err=True) -> Union[Path, bool]:
    """Return path if check passed, else raise error.
    check_fn: one of 'exists', 'is_dir', 'is_file'.
    if raise_err=False, return False instead of err.
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
        raise FileNotFoundError(msg)

    return pathname


def subprocess_run(cmd:str, capture_output=True, check:bool=False,
                   text=True, shell=True) -> Union[subprocess.CompletedProcess,
                                                   subprocess.CalledProcessError]:
    """Wraps subprocess.run. Return CompletedProcess or err obj."""

    try:
        data = subprocess.run(cmd,
                              capture_output=capture_output,
                              check=check,
                              text=text,
                              shell=shell
                             )
    except subprocess.CalledProcessError as e:
        data = e

    return data


def make_executable(sh_path:str) -> None:
    """Alternative to os.chmod(sh_path, stat.S_IXUSR): permission denied."""

    sh_path = Pathok(sh_path)
    cmd = f"chmod +x {str(sh_path)}"

    p = subprocess_run(cmd,
                       capture_output=False,
                       check=True)
    if isinstance(p, subprocess.CalledProcessError):
        logger.exception(f"Error in subprocess cmd 'chmod +x':\nException: {p}")
        raise

    return


def load_tsv(fpath:str, index_col:str=None) -> Union[pd.DataFrame, None]:
    """Read a tab-separated file into a pandas.DataFrame.
    Return None upon failure.
    """
    fp = Pathok(fpath, raise_err=False)
    if not fp:
        logger.error(f"Not found: {fp}")
        return None
    return pd.read_csv(fp, index_col=index_col, sep="\t")


def pk_to_float(value) -> float:
    """Out of bound values become +/-8888 or 9999 (curve too sharp)
    during conversion to float.
    """
    try:
        v = float(value)
    except ValueError:
        if value.startswith("titra"): #tion curve too sharp"
            return 9999.
        oob = value[0]  # oob sign, > or <
        if oob == "<":
            v = -8888.
        else:
            v = 8888.

    return v


def get_col_specs(collated:bool=False, titr_type:str='ph') -> tuple:
    """Return the columns spec for pd.fwf reader to read a 'pK.out' or a
    'all_pkas.out' file, and the header fields.

    The fields are returned so that they can be used for replacing some of the
    names that do not match the format width of the data.
    Args:
    collated (bool, False): Indicates whether the file is a collated pk.out file
                            or a single one (default)
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh', 'ch']
    """

    titr = titr_type.lower()
    if titr not in ["ph", "eh", "ch"]:
        raise ValueError("titr_type must be one of ['ph', 'eh', 'ch']")

    titr = titr.upper()

    # non collated header:
    pko_hdr = f"{titr} pKa/Em n(slope) 1000*chi2 vdw0 vdw1 tors ebkb dsol offset pHpK0 EhEm0 -TS residues total"
    if collated:
        pko_hdr = "PDB  resid@" + pko_hdr

    fields = pko_hdr.split()
    # field width: no space between fields of width 8:
    #line_frmt = "{:<4s} {:<14s}{:9.3f} {:9.3f} {:9.3f}  {:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:10.2f}"
    fwd_collated = [4, 14, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 10]

    if collated:
        wd = fwd_collated
    else:
        wd = fwd_collated[1:]

    N = len(wd)
    cs = []
    start, next = 0, 0
    for i in range(N):
        next = wd[i]
        cs.append((start, start+next))
        if next == 8:
            start += next
        else:
            start += next + 1

    return cs, fields


def get_sumcrg_hdr(bench_dir:str) -> str:
   """Used for colspecs -> df."""

   hdr0 = "  pH           0     1     2     3     4     5     6     7     8     9    10    11    12    13    14"
   def_flds = len(hdr0.strip().split())

   run_dir = get_mcce_env_dir(bench_dir)
   cmd = f"head -n1 {str(run_dir)}/sum_crg.out"
   out = subprocess_run(cmd)
   if isinstance(out, subprocess.CompletedProcess):
       hdr = out.stdout.splitlines()[0]
   flds = len(hdr.strip().split())
   if flds != def_flds:
       return hdr
   else:
       return hdr0


def get_sumcrg_col_specs(collated:bool=False, titr_type:str='ph', hdr:str=None) -> tuple:
    """
    Return the columns spec for pd.fwf reader to read a 'sum_crg.out' or
    'all_sumcrg.out' file, and the header fields.
    Used by comparison.py.

    The fields are returned so that they can be used for replacing some of the
    names that do not match the format width of the data.
    Args:
    collated (bool, False): Indicates whether the file is a collated sum_crg.out file
                            or a single one (default)
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh', 'ch']
    """

    titr = titr_type.upper()
    if hdr is None:      # default:
        fwd_collated = [4, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
        # non collated header:
        hdr = f"{titr} 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
        #sumcrg frmt:  "  pH      " + " %5d" * points :: 2+2+6, " %5d" * p
    else:
        hdr = hdr.strip()
        titr, *nums = hdr.split()
        fwd_collated = [4, 10] + [5 for _ in nums]

    if collated:
        hdr = "PDB  resid@" + hdr
    fields = hdr.split()

    if collated:
        wd = fwd_collated
    else:
        wd = fwd_collated[1:]

    N = len(wd)
    cs = []
    start, next = 0, 0
    for i in range(N):
        next = wd[i]
        cs.append((start, start+next))
        start += next + 1

    return cs, fields


def fout_df(out_fp:str, collated:bool=False, titr_type:str="ph", kind:str="pk.out") -> Union[pd.DataFrame, None]:
    """Load a file that has the same format as 'pK.out'; it can be either
    a single 'pK.out', 'sum_crg.out' file or a file that is collation of many:
    'all_pkas.out', 'all_sumcrg.out' in which case, 'collated' must be True.
    Args:
      out_fp (str): file path
      collated (bool, False): Whether the file format is that of a single file or not.
      titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh', 'ch']
      kind (str, 'pk.out'): Format of the out file.

    Return a pandas.DataFrame or None upon failure.
    Note: oob values: +/8888, 9999
    """

    fp = Pathok(out_fp, raise_err=False)
    if not fp:
        logger.error(f"Not found: {fp}")
        return None

    titr = titr_type.lower()
    if titr not in ["ph", "eh", "ch"]:
        raise ValueError("titr_type must be one of ['ph', 'eh', 'ch']")

    is_pko = kind.lower() == "pk.out"
    if is_pko:
        colspecs, cols = get_col_specs(collated=collated, titr_type=titr)
    else:
        #get env to get sumcrg_hdr
        if collated:
            bench = fp.parent.parent
        else:
            bench = fp.parent
        sc_hdr = get_sumcrg_hdr(bench)
        colspecs, cols = get_sumcrg_col_specs(collated=collated, titr_type=titr, hdr=sc_hdr)

    df = pd.read_fwf(fp, colspecs=colspecs, index_col=0)
    # rm 1st col that became index:
    df.rename(columns=dict(zip(df.columns, cols[1:])), inplace=True)
    if is_pko:
        # convert pK/Em vals to float:
        df["pKa/Em"] = df["pKa/Em"].apply(pk_to_float)

    return df


def get_book_dirs_for_status(book_fpath:str, status:str="c") -> list:
    """Return a list of folder names from book_fp, the Q_BOOK file path,
    if their status codes match 'status', i.e. completed ('c', default),
    or errorneous ('e').
    """

    status = status.lower()
    if not status or status not in ["c", "e"]:
        logger.error("Invalid 'status'; choices are 'c' or 'e'")
        raise ValueError("Invalid 'status'; choices are 'c' or 'e'")

    book_fp = Pathok(book_fpath)
    book_dirs = []
    with open(book_fp) as book:
        for line in book:
            # select the portion preceding any appended comment
            rawtxt = line.strip().split("#")[0]
            fields = rawtxt.split()
            if len(fields) == 2:
                if fields[1].lower() == status:
                    book_dirs.append(fields[0])

    return book_dirs


def to_pickle(obj, fp):
   pickle.dump(obj, open(fp, "wb"))


def from_pickle(fp):
   obj = pickle.load(open(fp, "rb"))
   return obj
