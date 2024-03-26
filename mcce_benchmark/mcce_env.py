#!/usr/bin/env python

"""
Module: mcce_env.py

Modified version of ENV class from Stable-MCCE/bin/pdbio.py:
  - Simplified: Only 2 methods: load_runprm,  __str__;
  - Needs "rundir_path" Path as class parameter
  - Attributes:
    self.runprm: dict
    self.rundir: Path
"""

from mcce_benchmark import BENCH, RUNS_DIR, SUB1
import logging
from pathlib import Path
import subprocess
from typing import Union


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class ENV:
    def __init__(self, rundir_path:str) -> dict:
        self.rundir = Path(rundir_path)
        # run.prm parameters key:value
        self.runprm = {}
        self.sumcrg_hdr = ""

        self.load_runprm()

    def load_runprm(self):
        # Only run.prm.record is a valid file for comparing two runs!
        fp = Path(self.rundir.joinpath("run.prm.record"))
        if not fp.exists():
            logger.error(f"Not found: run.prm.record in {self.rundir}")
            raise e(f"Not found: run.prm.record in {self.rundir}")

        with open(fp) as fin:
            lines = fin.readlines()

        for line in lines:
            entry_str = line.strip().split("#")[0]
            fields = entry_str.split()
            if len(fields) > 1:
                key_str = fields[-1]
                if key_str[0] == "(" and key_str[-1] == ")":
                    key = key_str.strip("()").strip()
                    # inconsistant output in run.prm.record:
                    if key == "EPSILON_PROT":
                        value = round(float(fields[0]),1)
                    else:
                        value = fields[0]
                self.runprm[key] = value

        return

    def __str__(self):
        out = f"rundir: {self.rundir}\nrunprm dict:\n"
        for k in self.runprm:
            out = out + f"{k} : {self.runprm[k]}\n"
        return out


def valid_envs(env1:ENV, env2:ENV) -> tuple:
    """
    Return a 2-tuple:
        (bool, # True: valid,
         error/info message: includes differing keys).
    Step 6 params: excluded from diffing: run1 and run2 are still comparable if only one has run step 6
    """

    s6_keys = {'GET_HBOND_MATRIX',
               'GET_HBOND_NETWORK',
               'HBOND_ANG_CUTOFF',
               'HBOND_LOWER_LIMIT',
               'HBOND_UPPER_LIMIT',
               'MS_OUT', # set in step4 if step6 has run
              }
    # For warning:
    path_keys = {"DELPHI_EXE", "MCCE_HOME"}
    all_keys = set(env1.runprm).union(set(env2.runprm))
    # not always there or nightmare to compare:
    all_keys.remove("EXTRA")
    all_keys.remove("RENAME_RULES")

    # populate diff dict:
    delta = {}
    msg = "OK"

    for k in all_keys:
        if not k in s6_keys:
            v1 = env1.runprm.get(k, None)
            v2 = env2.runprm.get(k, None)
            if v1 is None or v2 is None or v1 != v2:
                delta[k] = [('env1', v1), ('env2', v2)]

    n_delta = len(delta)
    if n_delta == 0:
        return True, msg

    if n_delta > 1:
        if set(delta.keys()) == path_keys:
            msg = "These path keys differ between the two run sets.\n"
            for k in delta:
                msg += f"{k}\t:\t{delta[k]}\n"
            return True, msg

        msg = "A valid comparison requires only one differing parameter between the two run sets.\n"
        msg = msg + f"{len(delta)} were found:\n"
        for k in delta:
            msg += f"{k}\t:\t{delta[k]}\n"

    else: #len == 1: check value of TITR_TYPE
        if delta.get("TITR_TYPE", None) is not None:
            msg = "A valid comparison requires the two run sets to have the same TITR_TYPE.\n"
            msg = msg + f"TITR_TYPE found: {delta}\n."
            return False, msg

    return True, msg


def get_ref_set(refset_name:str, subcmd:str = SUB1) -> Path:
    if subcmd != SUB1:
        msg = "'parse.e4' is the only reference available & applies to pH titrations setup with `bench_setup pkdb_pdbs"
        logger.error(msg)
        raise ValueError(msg)

    fp = Path(BENCH.BENCH_PH_REFS.joinpath(refset_name))

    return fp


def get_mcce_env_dir(bench_dir:str,
                     subcmd:str = SUB1,
                     is_refset:bool = False) -> Union[Path, None]:
    """Return a path where to get run.prm.record."""

    if is_refset and subcmd != SUB1:
        raise ValueError(f"The reference dataset {bench_dir} is only available via {SUB1}.")

    if is_refset:
        # then bench_dir is the name of a reference dataset
        bdir = get_ref_set(bench_dir, subcmd=subcmd)
    else:
        bdir = Path(bench_dir)

    runs_dir = Path(bdir.joinpath(RUNS_DIR))
    for fp in runs_dir.iterdir():
        if fp.is_dir:
            return fp

    return


def get_run_env(bench_dir:str,
                subcmd:str = SUB1,
                is_refset:bool = False)-> ENV:

    bench_dir = Path(bench_dir)
    run_dir = get_mcce_env_dir(bench_dir,
                               subcmd=subcmd,
                               is_refset=is_refset)
    env = ENV(run_dir)
    return env


def validate_envs(bench_dir1:str, bench_dir2:str,
                  subcmd:str = SUB1,
                  dir2_is_refset:bool = False) -> tuple:
    """Wrapper for fetching a run dir, instanciating the envs, and validating them.
       Return the 2-tuple from valid_envs: bool, msg.
    """

    env1 = get_run_env(bench_dir1, subcmd=subcmd)
    env2 = get_run_env(bench_dir2,
                       subcmd=subcmd,
                       is_refset=dir2_is_refset)

    return valid_envs(env1, env2)


def get_sumcrg_hdr(bench_dir:str) -> str:
   """Used for colspecs -> df.
   Return header if not default."""

   hdr0 = "  pH           0     1     2     3     4     5     6     7     8     9    10    11    12    13    14"
   def_flds = len(hdr0.strip().split())

   run_dir = get_mcce_env_dir(bench_dir)
   cmd = f"head -n1 {str(run_dir)}/sum_crg.out"
   out = subprocess.run(cmd)
   if isinstance(out, subprocess.CompletedProcess):
       hdr = out.stdout.splitlines()[0]
       flds = len(hdr.strip().split())
       if flds != def_flds:
           return hdr

   return None
