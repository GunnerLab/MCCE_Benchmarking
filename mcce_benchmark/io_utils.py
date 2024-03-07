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
def pkout_df(pko_fp:str, collated:bool=False, titr_type:str='ph') -> Union[pd.DataFrame, None]
def json_to_dict(json_fp:str) -> dict:
def dict_to_json(d:dict, json_fp:str) -> None:
"""

from mcce_benchmark import BENCH, ENTRY_POINTS, OUT_FILES, ANALYZE_DIR, DEFAULT_DIR
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
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
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh']
    """

    titr = titr_type.lower()
    if titr not in ["ph", "eh"]:
        raise ValueError("titr_type must be one of ['ph', 'eh']")

    if titr == "ph":
        titr = "pH"
    else:
        titr = "Eh"

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


def pkout_df(pko_fp:str, collated:bool=False, titr_type:str='ph') -> Union[pd.DataFrame, None]:
    """Load a file that has the same format as 'pK.out'; it can be either
    a single 'pK.out' file or a file that is collation of many as with 'all_pkas.out',
    in which case, 'collated' must be True.
    Args:
      pko_fp (str): file path to the pkout file
      collated (bool, False): Whether the file format is that of a single file or not.
      titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh']
    Return a pandas.DataFrame or None upon failure.
    Note: oob values: +/8888, 9999
    """

    fp = Pathok(pko_fp, raise_err=False)
    if not fp:
        logger.error(f"Not found: {fp}")
        return None

    titr = titr_type.lower()
    if titr not in ["ph", "eh"]:
        raise ValueError("titr_type must be one of ['ph', 'eh']")

    colspecs, cols = get_col_specs(collated=collated, titr_type=titr)
    df = pd.read_fwf(fp, colspecs=colspecs, index_col=0)
    # rm 1st col that became index:
    df.rename(columns=dict(zip(df.columns, cols[1:])), inplace=True)
    # convert pK/Em vals to float:
    df["pKa/Em"] = df["pKa/Em"].apply(pk_to_float)

    return df


def json_to_dict(json_fp:str) -> dict:
    jsfp = Pathok(json_fp)
    with open(jsfp) as fp:
        data = json.load(fp)

    return data


def dict_to_json(d:dict, json_fp:str) -> None:
    with open(json_fp, "w") as fp:
        json.dump(d, fp)
    return
