#!/usr/bin/env python

"""
Cli end point for comparison of two sets of runs. `compare`.

Cli parser with 2 sub-commands with same options:
  -dir1 <path/to/set/of/runs1>; must exists
  -dir2 <path/to/set/of/runs2>; must exists

1. pkdb_pdbs (SUB1)
2. user_pdbs (SUB2)
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace
from mcce_benchmark import BENCH, ENTRY_POINTS, SUB1, SUB2
from mcce_benchmark import FILES, ANALYZE_DIR, RUNS_DIR
from mcce_benchmark.mcce_env import ENV, get_run_env
from mcce_benchmark import plots
from mcce_benchmark.cleanup import clear_folder
from mcce_benchmark.io_utils import Pathok, subprocess_run, subprocess
from mcce_benchmark.io_utils import get_book_dirs_for_status, get_sumcrg_hdr, pk_to_float
from mcce_benchmark.io_utils import fout_df, to_pickle, tsv_to_df
from mcce_benchmark.scheduling import clear_crontab
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_mcce_version(pdbs_dir:str) -> None:
    """MCCE version(s) from run.log files ->VERSIONS file."""

    pdbs_fp = Pathok(pdbs_dir, raise_err=False)
    if not pdbs_fp:
        return None

    pdbs_dir = Path(pdbs_dir)
    pdbs = str(pdbs_dir)
    cmd = (f"grep -m1 'Version' {pdbs}/*/run.log | awk -F: '/Version/ "
           + "{print $2 $3}' | sort -u")
    out = subprocess_run(cmd)
    if out is subprocess.CalledProcessError:
        logger.error("Error fetching Version.")
        return

    msg = [f"MCCE Version(s) found in run.log files:\n"]
    for v in [o.strip() for o in out.stdout.splitlines()]:
        msg.append(f"\t{v}\n")
    ver_fp = pdbs_dir.parent.joinpath(ANALYZE_DIR, FILES.VERSIONS.value)
    with open(ver_fp, "w") as f:
        f.writelines(msg)

    return

# for multi-protein runs
def collate_all_sumcrg(bench_dir:str, run_env:ENV, titr_type:str="ph") ->None:

    bench = Pathok(bench_dir)
    dirpath = bench.joinpath(RUNS_DIR)
    d = str(dirpath)

    # output dir
    analyze = bench.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()
    # out file
    all_out = analyze.joinpath(FILES.ALL_SUMCRG.value)
    all_out_s = str(all_out)

    hdr = get_sumcrg_hdr(bench)
    titr = hdr.strip().split()[0]

    ofs = '":"'
    cmd = "awk 'BEGIN{OFS=" + ofs + "}{out = substr(FILENAME, length(FILENAME)-15, 4); print out, $0}' "
    cmd = cmd + f"{d}/*/sum_crg.out | sed -e '/----------/d' -e '/  {titr}/d' > {d}/all_out; "
    cmd = cmd + f"sed '1 i\{hdr}' {d}/all_out > {all_out_s};"  # add header back
    cmd = cmd + f" /bin/rm {d}/all_out"

    data = subprocess_run(cmd, capture_output=False) #check=True)
    if isinstance(data, subprocess.CompletedProcess):
        logger.info(f"Created {all_out!r}; Can be loaded using pkanalysis.all_pkas_df(bench_dir).")
    else:
        logger.exception(f"Subprocess error")
        raise data # data holds the error obj

    return


def collate_all_pkas(bench_dir:str, titr_type:str="ph") ->None:
    """Collate all pK.out files from 'bench_dir'/runs, into analysis/ALL_PKAS.
       Retain the same fixed-witdth format => extension = ".out".
       This file can be loaded using either one of these functions:
         - pkanalysis.all_pkas_df(bench_dir)
         - pkanalysis.fout_df(pko_fp, collated=True)
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh', 'ch']
    """

    bench = Pathok(bench_dir)
    bench_s = str(bench)
    d = Pathok(bench.joinpath(RUNS_DIR))
    dirpath = str(d)

    # output dir
    analyze = bench.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()
    # out file
    all_out = analyze.joinpath(FILES.ALL_PKAS.value)
    all_out_s = str(all_out)

    titr = titr_type.lower()
    if titr not in ["ph", "eh", "ch"]:
        raise ValueError("titr_type must be one of ['ph', 'eh', 'ch']")
    titr = titr.upper()

    pko_hdr = f"PDB  resid@{titr}         pKa/Em  n(slope) 1000*chi2      vdw0    vdw1    tors    ebkb    dsol   offset  pHpK0   EhEm0    -TS   residues   total"
    # offset = len("pk.out") + 4 = 10
    ofs = '":"'
    RUNS = '"' + RUNS_DIR + '"'
    cmd = "awk 'BEGIN{OFS=" + ofs + "}{idx = index(FILENAME," + RUNS + ")+5; out = substr(FILENAME, length(FILENAME)-6-idx); print out, $0}' "
    cmd = cmd + f"{dirpath}/*/pK.out | sed '/total$/d' > {dirpath}/all_pkas; "
    cmd = cmd + f"sed '1 i\{pko_hdr}' {dirpath}/all_pkas > {all_out_s};"  # add header back
    cmd = cmd + f" /bin/rm {dirpath}/all_pkas"

    data = subprocess_run(cmd, capture_output=False) #check=True)
    if isinstance(data, subprocess.CompletedProcess):
        logger.info(f"Created {all_out!r};\n\tCan be loaded using pkanalysis.fout_df(allfp, collated=True, titr_type='ph').")
    else:
        logger.exception(f"Subprocess error")
        raise data # data holds the error obj
    return


def get_oob_mask(df):
    """Create a mask on df for 'pKa/Em' values out of bound."""

    try:
        msk = (abs(df["pKa/Em"]) == 8888.) | (df["pKa/Em"] == 9999.)
        return msk
    except KeyError as e:
        raise e("Wrong dataframe: no 'pKa/Em' columns.")


def all_pkas_df(path:str, titr_type:str="ph", reduced_ok=True) -> Union[pd.DataFrame, None]:
    """Load <bench_dir>/analysis/all_pkas.out into a pandas DataFrame;
    Return  a pandas.DataFrame or None upon failure.
    Version of 'pkanalysis.fout_df' with pre-set 'all_pkas.out' file.

    Args:
    path (str): Can be bench_dir or a file path.
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh', 'ch']
    reduced_ok (bool, True): Load ALL_PKAS_TSV (with oob pkas processed out if found), else
                         load all_pkas.out (complete file)
    """

    p = Pathok(path, raise_err=False)
    if not p:
        logger.error(f"Not found: {p}")
        return None

    if p.is_file(): # and p.name == FILES.ALL_PKAS.value:
        allfp = p
    else:
        # bench_dir
        allfp = p.joinpath(ANALYZE_DIR, FILES.ALL_PKAS.value)

    if not allfp.exists():
        logger.error(f"Not found: {allfp}; this file is created via pkanalysis.collate_all_pkas(bench_dir).")
        return None

    titr = titr_type.lower()
    if titr not in ["ph", "eh", "ch"]:
        raise ValueError("titr_type must be one of ['ph', 'eh', 'ch']")

    if reduced_ok:
        # load tsv file if found (created by extract_oob_pkas):
        all_tsv = allfp.parent.joinpath(FILES.ALL_PKAS_TSV.value)
        if all_tsv.exists():
            logger.info("Loading FILES.ALL_PKAS_TSV")
            return tsv_to_df(all_tsv, index_col=0) #collated=True, titr_type=titr)

    return fout_df(allfp, collated=True, titr_type=titr)


def extract_oob_pkas(bench_dir:str):
    """Load all_pkas.tsv into df;
    Extract and save out of bounds values.
    Rewrite all_pkas.tsv without them.
    """

    bench = Path(bench_dir)
    # Load all_pkas file, all_pkas.out:
    allout_df = all_pkas_df(bench)
    # convert pK/Em vals to float:
    allout_df["pKa/Em"] = allout_df["pKa/Em"].apply(pk_to_float)

    #extract oob if any
    msk = get_oob_mask(allout_df)
    oob_df = allout_df[msk]
    if oob_df.shape[0]:
        analyze = bench.joinpath(ANALYZE_DIR)

        oob_fp = analyze.joinpath(FILES.ALL_PKAS_OOB.value)
        oob_df.to_csv(oob_fp, sep="\t")

        # Reset all_pkas.out
        allout_df = allout_df[~msk]
        all_fp = analyze.joinpath(FILES.ALL_PKAS_TSV.value)
        allout_df.to_csv(all_fp, sep="\t")
    else:
        logger.info(f"No out of bound pKa values in {FILES.ALL_PKAS.value}")

    return


def all_run_times_to_tsv(pdbs_dir:str, overwrite:bool=False) -> None:
    """Return mcce step times from run.log saved to a tab-separated file."""

    pdbs = Pathok(pdbs_dir)
    # output dir
    analyze = pdbs.parent.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    cmd = "awk '/Total time/ {len=length(FILENAME); print substr(FILENAME,len-11,4), $4, NF-1}' "
    cmd = cmd + str(pdbs) + "/*/run.log | sed 's/MC:/step4/'"
    out = subprocess_run(cmd)
    if out is subprocess.CalledProcessError:
        logger.error("Error fetching run times.")
        return

    fp = analyze.joinpath(FILES.RUN_TIMES.value)
    if fp.exists():
        if overwrite:
            fp.unlink()
        else:
            #logger.info(f"File already exists: {fp}")
            return

    time_list = ["\t".join(line.split()) + "\n" for line in out.stdout.splitlines()]
    with open(fp, "w") as o:
        o.writelines(["PDB\tstep\tseconds\n"])
        o.writelines(time_list)

    return


def get_step2_count(step2_out_path:str, kind:str) -> int:
    """Return the count of items given by `kind` from a step2_out.pdb file. """

    if kind == "res":
        cmd = "awk '{print $4, substr($5,1,5)}' " + f"{step2_out_path} |uniq|sed -e '/^NTR/d; /^CTR/d'|wc -l"
    elif kind == "confs":
        cmd = "awk '{print $5}' " + f"{step2_out_path} | uniq | wc -l"
    else:
        logger.error(f"kind must be one of ['res','confs']; Given: {kind}.")
        raise ValueError(f"kind must be one of ['res','confs']; Given: {kind}.")

    data = subprocess_run(cmd)
    if isinstance(data, subprocess.SubprocessError):
        logger.exception(f"Error fetching {kind} count.")
        raise data
    elif not data.stdout.strip():
        logger.info(f"No count from step2_out.pdb in {Path(step2_out_path).parent.name}")
        return 0

    return int(data.stdout.strip())


def all_counts_to_tsv(pdbs_dir:str, kind:str, overwrite:bool=False) -> None:
    """Save the count of items given by `kind` from step2_out.pdb in all subfolders
    of pdbs_dir to a tab-separated file; format: DIR \t n.
    """

    pdbs = Pathok(pdbs_dir)

    kind = kind.lower()
    if kind not in ["res","confs"]:
        logger.error(f"'kind' must be one of ['res','confs']; Given: {kind}.")
        raise ValueError(f"'kind' must be one of ['res','confs']; Given: {kind}.")

    # output dir
    analyze = pdbs.parent.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    fname = FILES.CONF_COUNTS.value
    if kind == "res":
        fname = FILES.RES_COUNTS.value

    fp = analyze.joinpath(fname)
    if fp.exists():
        if overwrite:
            fp.unlink()
        else:
            #logger.info(f"File already exists: {fp}")
            return

    count_list = []
    for dp in pdbs.glob("./*/step2_out.pdb"):
        N = get_step2_count(str(dp), kind=kind)
        count_list.append(f"{dp.parent.name}\t{N}\n")

    with open(fp, "w") as o:
        o.writelines([f"PDB\t{kind}\n"])
        o.writelines(count_list)

    return


def confs_per_res_to_tsv(pdbs_dir:str, overwrite:bool=False) -> None:
    """Save conf per res to tsv. """

    pdbs = Pathok(pdbs_dir)
    # output dir
    analyze = pdbs.parent.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    # confs file:
    all_counts_to_tsv(pdbs, kind="confs", overwrite=overwrite)
    tsv_count = analyze.joinpath(FILES.CONF_COUNTS.value)
    # res file:
    all_counts_to_tsv(pdbs, kind="res", overwrite=overwrite)
    tsv_res = analyze.joinpath(FILES.RES_COUNTS.value)

    df_res = pd.read_csv(tsv_res, sep="\t")
    df_res.set_index("PDB", inplace=True)
    df_res.sort_index(inplace=True)

    df_confs = pd.read_csv(tsv_count, sep="\t")
    df_confs.set_index("PDB", inplace=True)
    df_confs.sort_index(inplace=True)

    df = df_confs.merge(df_res, on="PDB")
    df["confs_per_res"] = round(df.confs/df.res,2)

    #final output:
    tsv_fin = analyze.joinpath(FILES.CONFS_PER_RES.value)
    if tsv_fin.exists() and overwrite:
        tsv_fin.unlink()

    df.to_csv(tsv_fin, sep="\t")

    return


def confs_throughput_to_tsv(pdbs_dir:str, overwrite:bool=False) -> pd.DataFrame:
    """
    Obtain and save the average time & conformer throughput per step in a tab
    separated file, FILES.CONFS_THRUPUT.
    """

    pdbs = Pathok(pdbs_dir)
    # output dir
    analyze = pdbs.parent.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    # times file:
    tsv_time = analyze.joinpath(FILES.RUN_TIMES.value)
    if tsv_time.exists() and overwrite:
        tsv_time.unlink()
        all_run_times_to_tsv(pdbs, overwrite=overwrite)

    df_time = pd.read_csv(tsv_time, sep="\t")
    df_time.set_index("PDB", inplace=True)
    df_time.sort_index(inplace=True)

    # confs file:
    tsv_count = analyze.joinpath(FILES.CONF_COUNTS.value)
    if tsv_count.exists() and overwrite:
        tsv_count.unlink()
    all_counts_to_tsv(pdbs, kind="confs", overwrite=overwrite)

    df_confs = pd.read_csv(tsv_count, sep="\t")
    df_confs.set_index("PDB", inplace=True)
    df_confs.sort_index(inplace=True)

    df = df_confs.merge(df_time, on="PDB")
    df["confs_per_sec"] = round(df.confs/df.seconds,2)
    df["per_min_thrup"] = round(df.confs_per_sec * 60,2)

    #final output:
    tsv_fin = analyze.joinpath(FILES.CONFS_THRUPUT.value)
    if tsv_fin.exists() and overwrite:
        tsv_fin.unlink()

    gp = df.groupby(by="step", as_index=True).aggregate('mean')
    gp.to_csv(tsv_fin, sep="\t")

    return


def pct_completed(book_fpath:str) -> float:
    """Return the pct of runs that are completed or finished with error."""

    book_fp = Pathok(book_fpath)
    # 2 cmds:
    cmd = f"grep '[ce]$' {book_fp} |wc -l; cat {book_fp} |wc -l"
    data = subprocess_run(cmd)
    if isinstance(data, subprocess.SubprocessError):
        logger.error(f"Error fetching pct completed.")
        return

    if not data.stdout.strip():
        logger.info("No data from book file")
        return

    out = data.stdout.splitlines()
    pct = float(out[0])/float(out[1])

    return pct


def job_pkas_to_dict(book_fpath:str) -> dict:
    """
    Uses the 'q-book' file to retrieve COMPLETED jobs, together with all_pks.out
    instead of iterating over subfolders (which may not be there.)

    Origin: pkanalysis.py/read_calculated_pkas
    Canonical dir struc: book_fpath points to <benchmark_dir>/runs/book.txt
    Uses <bench_dir>/analysis/all_pkas.out
    """

    book_fp = Pathok(book_fpath)
    completed_dirs = get_book_dirs_for_status(book_fp) # default 'c'

    calc_pkas = {}
    all_out_fp = book_fp.parent.parent.joinpath(ANALYZE_DIR, FILES.ALL_PKAS.value)

    # all pkas df: all 'in bounds' pk values if tsv version exists; floats
    allout_df = all_pkas_df(all_out_fp)
    c_resid, c_pk = allout_df.columns[:2]

    for dir in completed_dirs:
        pk_df = allout_df.loc[dir]      # filter for this dir
        for r, row in pk_df.iterrows():
            resid = row[c_resid]
            if resid.startswith("NTG"):
                resid = "NTR" + resid[3:]
            key = (dir, resid)
            calc_pkas[key] = row[c_pk]

    return calc_pkas


def to_float(value:str):
    """Conversion function to be used in pd.read_csv.
    Return numpy.nan on conversion failure.
    """
    try:
        new = float(value)
    except:
        new = np.nan
    return new


def to_upper(value:str):
    """Conversion function to be used in pd.read_csv."""
    return str(value).upper()


def experimental_pkas_to_dict() -> dict:
    """Origin: pkanalysis.py/read_experiment_pkas
    Uses package resources BENCH.BENCH_WT.
    """

    res_to_mcce = {"ARG": "ARG+",
                   "HIS": "HIS+",
                   "LYS": "LYS+",
                   "N-TERM": "NTR+",
                   "ASP": "ASP-",
                   "GLU": "GLU-",
                   "C-TERM": "CTR-",
                   "CYS": "CYS-",
                   "TYR": "TYR-"}

    pkas_df = pd.read_csv(BENCH.BENCH_WT,
                          usecols=["PDB ID", "Res Name", "Chain", "Res ID", "Expt. pKa"],
                          comment="#",
                          converters={"PDB ID":to_upper,
                                      "Res Name":to_upper,
                                      "Expt. pKa": to_float,
                                     },
                          ).dropna(how="any")
    pkas_df.sort_values(by="PDB ID", inplace=True, ignore_index=True)

    expl_pkas = {}
    for _, row in pkas_df.iterrows():
        key = (row["PDB ID"],
               f'{res_to_mcce[row["Res Name"]]}{row["Chain"]}{int(row["Res ID"]):04d}_')
        expl_pkas[key] = row["Expt. pKa"]

    return expl_pkas


def match_pkas(calc_pkas:dict, expl_pkas:dict) -> list:
    """Return a list of 3-tuples:
    Convention: second dict is taken as ref.
    (id=<pdb>/<res>, calculated pka, experimental pka).
    """

    calculated_ids = list(set([key[0] for key in calc_pkas]))
    pkas = []
    for key in expl_pkas:
        if key[0] not in calculated_ids:
            continue

        if key in calc_pkas:
            calc_pka = calc_pkas[key]
        elif key[1][3] == "-":
            calc_pka = 0.0
        elif key[1][3] == "+":
            calc_pka = 14.0
        else:
            logger.error(f"Parsing error of job pKas for {key}")

        pkas.append(("{}/{}".format(*key), calc_pka, expl_pkas[key]))

    return pkas


def matched_pkas_to_csv(fpath:str, matched_pkas:list, kind:str=SUB1) -> None:
    """Write a list of 3-tuples (as in a matched pkas list) to a txt file."""

    fp = Path(fpath)
    if kind == SUB1:
        hdr = "key,mcce,expl\n"
    else:
        hdr = "key,set1,set2\n"
    with open(fp, "w") as fh:
        fh.writelines(hdr) # header
        fh.writelines("{},{},{}\n".format(*pka) for pka in matched_pkas)

    return


def matched_pkas_to_df(matched_fp:str) -> pd.DataFrame:
    """
    Load MATCHED_PKAS csv file into a pandas DataFrame.
    PRE: file MATCHED_PKAS csv file created via mcce_benchmark.pkanalysis.
    """

    fh = Path(matched_fp)
    if fh.name != FILES.MATCHED_PKAS.value:
        logger.error(f"Only {FILES.MATCHED_PKAS.value} is a valid file name.")
        raise ValueError(f"Only {FILES.MATCHED_PKAS.value} is a valid file name.")

    if not fh.exists():
        logger.error(f"Not found: {fh}; run pkanalysis to create.")
        raise FileNotFoundError(f"Not found: {fh}; run pkanalysis to create.")

    df = pd.read_csv(matched_fp)
    df[["PDB", "resid"]] = df.key.str.split("/", expand=True)
    df.drop(columns=["PDB","key"], inplace=True)

    try:
        df = df[["resid", "mcce", "expl"]]
    except KeyError:
        df = df[["resid", "set1", "set2"]]

    return df


def matched_pkas_stats(matched_df:pd.DataFrame,
                       subcmd:str=SUB1,
                       prec:int=2) -> dict:
    """Return a dictionnary:
       d_out = {"fit":(m, b),
                "N":N,
                "mean_delta": mean_delta,
                "rmsd":rmsd,
                "bounds":comp_bounds,
                "report":pkas_stats}.
    """

    np.seterr(all='raise')
    
    N = matched_df.shape[0]
    converged = True
    err_msg = ""
    try:
        m, b = np.polyfit(matched_df.mcce, matched_df.expl, 1)
    except Exception as e:
        #(np.linalg.LinAlgError, RuntimeWarning, FloatingPointError, RankWarning) as e:
        #RankWarning: Polyfit may be poorly conditioned
        #RuntimeWarning: invalid value encountered in divide
        #("SVD did not converge in Linear Least Squares")
        converged = False
        err_msg = str(e)
        m, b = 0,0

    # col1:A: calc - col2:B: ref (calc or expl)
    A = matched_df.iloc[:,1]
    B = matched_df.iloc[:,2]
    delta = abs(A - B)
    mean_delta = delta.mean(axis=None)
    rmsd = np.sqrt(np.mean(delta**2))

    if subcmd == SUB1:
        txt = f"""Residues stats:
Number of pKas matched with those in pKDB: {N:,}"""
        if converged:
            txt = txt + f"""
Fit line: y = {m:.{prec}f}.x + {b:.{prec}f}"""
        else:
            txt = txt + f"""
Fit line: None ({err_msg})"""
        txt = txt + f"""
Mean delta pKa: {mean_delta:.{prec}f}
RMSD, calculated vs experimental: {rmsd:.{prec}f}
"""
    else:
        txt = f"""Residues stats:
Number of pKas matched with those in set 2: {N:,}"""
        if converged:
            txt = txt + f"""
Fit line: y = {m:.{prec}f}.x + {b:.{prec}f}"""
        else:
            txt = txt + f"""
Fit line: None (Failed LLS fit)"""
        txt = txt + f"""
Mean delta pKa: {mean_delta:.{prec}f}
RMSD, set 1 vs set 2: {rmsd:.{prec}f}
"""

    comp_bounds = [3., 2., 1.]
    for b in comp_bounds:
        txt = txt + f"Proportion within {b} titr units: {delta[delta.le(b)].count()/N:.{prec}%}\n"

    d_out = {"fit":(m, b) if converged else f"None ({err_msg})",
             "N":N,
             "mean_delta": mean_delta,
             "rmsd":rmsd,
             "bounds":comp_bounds,
             "report":txt}

    return d_out


def res_outlier_count(matched_fp:str,
                      grp_by:str="res",
                      replace:bool=False,
                      bounds:tuple=(0,14)) -> pd.DataFrame:
    """Return counts per residue type for diff(col1-col2) > 3,
    and pKa values beyond titration bounds in a df.
    Save df to FILES.RES_OUTLIER or FILES.RESID_OUTLIER in the
    parent folder of matched_fp.
    Args:
    matched_fp (str): file path of matched pkas file;
    grp_by (str, "res"): one of ["res", "resid"];
    replace (bool, False): To overwrite existing file;
    bounds (tuple, (0,14)): Default titration bounds.
    """

    if grp_by not in ["res", "resid"]:
        logger.error(f"grp_by not in ['res','resid']: {grp_by}")
        raise ValueError(f"grp_by not in ['res','resid']: {grp_by}")

    matched_df = matched_pkas_to_df(matched_fp)
    N = matched_df.shape[0]
    
    if grp_by == "res":
        cols_pks = matched_df.columns.to_list()[-2:] 
        matched_df[["res", "resi"]] = matched_df.resid.str.split("[-|+]", expand=True)
        matched_df.drop(columns=["resi", "resid"], inplace=True)
        matched_df = matched_df[["res"]+cols_pks]

    set1 = matched_df.iloc[:,1]
    set2 = matched_df.iloc[:,2]
    idx_name = f"{grp_by.upper()} | {set1.name} v. {set2.name}"

    matched_df["delta"] = abs(set1 - set2)
    matched_df["Delta over 3"] = matched_df.delta > 3.0
    matched_df["Out of bounds"] = (abs(set1 - bounds[0]) < 0.01) | (abs(set1 - bounds[1]) < 0.01)
    matched_df.drop(columns=[set1.name, set2.name, "delta"], inplace=True)

    gp_oob = matched_df[matched_df["Out of bounds"]==True].groupby(grp_by).count()
    gp_oob.drop(columns="Delta over 3", inplace=True)
    N_over = gp_oob.shape[0]

    gp_del3 = matched_df[matched_df["Delta over 3"]==True].groupby(grp_by).count()
    gp_del3.drop(columns="Out of bounds", inplace=True)
    N_del3 = gp_del3.shape[0]

    out_df = gp_oob.merge(gp_del3, how='left', on=grp_by).replace({np.nan:0}).astype(int)
    oob_name = f"Out of bounds {bounds}"
    out_df.rename(columns={"Out of bounds": oob_name}, inplace=True)
    out_df.index.name = idx_name
    pcts = [f"{s/N:.0%}" for s in out_df.sum()]
    out_df.loc["pct"] = pcts

    if grp_by == "res":
        outlier_fp = Path(matched_fp).parent.joinpath(FILES.RES_OUTLIER.value)
    else:
        outlier_fp = Path(matched_fp).parent.joinpath(FILES.RESID_OUTLIER.value)

    if outlier_fp.exists() and replace:
        outlier_fp.unlink()
    out_df.to_csv(outlier_fp, sep="\t")

    return out_df


def analyze_runs(bench_dir:Path, subcmd:str):
    """Create all analysis output files."""

    bench = Pathok(bench_dir)
    # Get current set env; may need more than titr:
    env = get_run_env(bench, subcmd=subcmd)
    titr = env.runprm["TITR_TYPE"]

    pdbs = bench.joinpath(RUNS_DIR)
    book_fp = pdbs.joinpath(BENCH.Q_BOOK)

    analyze = bench.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()
    else:
        clear_folder(analyze)

    get_mcce_version(pdbs)

    logger.info(f"Collating pK.out and sum_crg.out files.")
    collate_all_sumcrg(bench, env, titr_type=titr)
    collate_all_pkas(bench, titr_type=titr)

    logger.info(f"Saving out of bounds pK values to tsv, if any.")
    extract_oob_pkas(bench)

    logger.info(f"Calculating conformers and residues counts into tsv files.")
    all_counts_to_tsv(pdbs, kind="confs", overwrite=True)
    all_counts_to_tsv(pdbs, kind="res", overwrite=True)
    all_run_times_to_tsv(pdbs, overwrite=True)
    confs_per_res_to_tsv(pdbs)

    logger.info(f"Calculating conformers thoughput into tsv files.")
    confs_throughput_to_tsv(pdbs)

    logger.info(f"Getting calculated pKas to dict.")
    # effective calculated pkas for all completed runs:
    calc_pkas = job_pkas_to_dict(book_fp)

    calcpk_fp = analyze.joinpath(FILES.JOB_PKAS.value)
    to_pickle(calc_pkas, calcpk_fp)

    if subcmd == SUB1:
        logger.info(f"Getting experimental pKas to dict.")
        expl_pkas = experimental_pkas_to_dict()
        #calc_pkas: done

        logger.info(f"Matching the pkas and saving list to csv file.")
        matched_pkas = match_pkas(calc_pkas, expl_pkas)
        matched_fp = analyze.joinpath(FILES.MATCHED_PKAS.value)
        matched_pkas_to_csv(matched_fp, matched_pkas)

        logger.info(f"Calculating the matched pkas stats into dict.")
        # no need for returned df here -> to tsv:
        _ = res_outlier_count(matched_fp)

        # matched_df: used by matched_pkas_stats and plots.plot_pkas_fit
        matched_df = matched_pkas_to_df(matched_fp)
        d_stats = matched_pkas_stats(matched_df)
        logger.info(d_stats["report"])
        pkl_fp = analyze.joinpath(FILES.MATCHED_PKAS_STATS.value)
        to_pickle(d_stats, pkl_fp)

    # plots
    logger.info(f"Plotting conformers throughput per step -> pic.")
    tsv = analyze.joinpath(FILES.CONFS_THRUPUT.value)
    thruput_df = tsv_to_df(tsv)
    save_to = analyze.joinpath(FILES.FIG_CONFS_TP.value)
    n_complete = len(get_book_dirs_for_status(book_fp))
    plots.plot_conf_thrup(thruput_df, n_complete, save_to)

    if subcmd == SUB1:
        logger.info(f"Plotting residues analysis -> pic.")
        save_to = matched_fp.parent.joinpath(FILES.FIG_FIT_PER_RES.value)
        plots.plot_res_analysis(matched_pkas, save_to)

        if isinstance(d_stats["fit"], str):
            logger.info("Data could not be fitted: no plot generated.")
        return

        logger.info(f"Plotting pkas fit -> pic.")
        save_to = matched_fp.parent.joinpath(FILES.FIG_FIT_ALLPKS.value)
        plots.plot_pkas_fit(matched_df, d_stats, save_to)

    return


#................................................................................
def pkdb_pdbs_analysis(args:Union[dict,Namespace]) -> None:
    """Processing tied to sub-command 1: pkdb_pdbs."""

    if isinstance(args, dict):
        args = Namespace(**args)
    analyze_runs(args.bench_dir, SUB1)
    return


def user_pdbs_analysis(args:Union[dict,Namespace]) -> None:
    """Processing tied to sub-command 2: user_pdbs."""

    if isinstance(args, dict):
        args = Namespace(**args)
    analyze_runs(args.bench_dir, SUB2)
    return


CLI_NAME = ENTRY_POINTS["analyze"] # as per pyproject.toml entry point

HELP_1 = """Sub-command for analyzing a benchmarking set against the pKaDBv1
using the same dataset and structure: <bench_dir>/runs folder."
"""

HELP_2 = f"""
Sub-command for analyzing a benchmarking set of user's pdbs.
"""

EPI = """
Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues
"""

DESC = f"""
Description:
Create analysis output files for a set of runs in <bench_dir>/analysis.

The main command is {CLI_NAME} along with one of 2 sub-commands:
- Sub-command 1: {SUB1}: analyze pKas against pKaDBv1;
- Sub-command 2: {SUB2}: analyze pKas for user's pdbs;

Output files:
    ALL_PKAS = "all_pkas.out"
    ALL_SUMCRG = "all_sumcrg.out"
    ALL_PKAS_OOB = "all_pkas_oob.tsv"    # out of bounds pKas
    JOB_PKAS = "job_pkas.pickle"                    # from dict
    CONF_COUNTS = "conf_counts.tsv"
    RES_COUNTS = "res_counts.tsv"
    RUN_TIMES = "run_times.tsv"
    CONFS_PER_RES = "confs_per_res.tsv"
    CONFS_THRUPUT = "confs_throughput.tsv"
    FIG_CONFS_TP = "confs_throughput.png"
    MATCHED_PKAS = "matched_pkas.csv"
    MATCHED_PKAS_STATS = "matched_pkas_stats.pickle" # from dict
    PKAS_STATS = "pkas_stats.csv"
    RES_OUTLIER = "outlier_residues.tsv"
    FIG_FIT_ALLPKS = "pkas_fit.png"
    FIG_FIT_PER_RES = "res_analysis.png"
"""

USAGE = f"""
{CLI_NAME} <+ sub-command :: one of [{SUB1}, {SUB2}]> <related args>\n

Examples:
   >{CLI_NAME} {SUB1} -bench_dir <path to dir>
   >{CLI_NAME} {SUB2} -bench_dir <path to dir>
"""

def analyze_parser():
    """Cli arguments parser with sub-commands for use in benchmark analysis. """

    def arg_valid_dirpath(p: str):
        """Return resolved path from the command line."""
        if not len(p):
            return None
        return Path(p).resolve()

    # parent parser
    p = ArgumentParser(
        prog = f"{CLI_NAME} ",
        description = DESC,
        #usage = USAGE,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = EPI,
    )

    subparsers = p.add_subparsers(required = True,
                                  title = f"{CLI_NAME} sub-commands",
                                  dest = "subparser_name",
                                  description = "Sub-commands of MCCE benchmarking analysis cli.",
                                  help = f"""The 2 choices for the benchmarking process:
                                  1) Analyze dataset of mcce runs viz pKaDBv1: {SUB1}
                                  2) FUTURE: Analyze two mcce runs
                                  """)

    sub1 = subparsers.add_parser(SUB1,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_1)
    sub1.add_argument(
        "-bench_dir",
        required = True,
        type = arg_valid_dirpath,
        help = """The user's directory where the /runs subfolder is setup.
        """
    )
    sub1.set_defaults(func=pkdb_pdbs_analysis)

    sub2 = subparsers.add_parser(SUB2,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_2)
    sub2.add_argument(
        "-bench_dir",
        required = True,
        type = arg_valid_dirpath,
        help = """The user's directory where the /runs subfolder is setup.
        """
    )
    sub2.set_defaults(func=user_pdbs_analysis)
    return p


def analyze_cli(argv=None):
    """
    Command line interface for MCCE benchmarking analysis entry point.
    """

    cli_parser = analyze_parser()
    args = cli_parser.parse_args(argv)

    # OK to analyze?
    bench = Pathok(args.bench_dir)
    book_fp = bench.joinpath(RUNS_DIR, BENCH.Q_BOOK)
    pct = pct_completed(book_fp)
    if pct < 1.:
        logger.info(f"Runs not 100% completed or failed, try again later; completed = {pct:.2f}")
        return
    clear_crontab()
    args.func(args)

    return


if __name__ == "__main__":

    analyze_cli(sys.argv[1:])
