#!/usr/bin/env python

"""
Cli end point for analysis. `analyze`

Cli parser with 2 sub-commands:

 1. expl_pkas:
   Option: -benchmarks_dir <path/to/dir/of/completed runs>; must exists

   Outputs: The Eum class `mcce_benchmark.OUT_FILES` holds all the file names.
   In <benchmarks_dir>: MATCHED_PKAS_FILE
   In <benchmarks_dir>/analysis:
     - residues & conformers count files;
     - plots saved as figures

 [2. mcce_runs: FUTURE ]
   Options:
   - "-new_calc_dir": path to a mcce output folder that will be compared
   - "-reference_dir": path to a mcce output folder for use as reference; default=parse.e4 (when ready)
   - "--plots": create & save plots
   - [FUTURE] "-reference_subdir" (list): If reference_dir is the default one, the list enables subsetting;
      e.g. if new_calc_dir was setup with only 2 pdbs found in parse.e4, then -reference_subdir=[1ANS,135L];
      Each item is a folder name for the pdb of the same name.
   - [FUTURE]: Add global list in __init__.py to read (virgin) book file (book.txt) as ALL_PDBS to facilitate subsetting of reference dataset.

   Outputs in "-new_calc_dir":
     - MATCHED_PKAS_FILE???????
     - pK.out diff
     - residues stats report

"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, Namespace as argNamespace
from mcce_benchmark import BENCH, ENTRY_POINTS, OUT_FILES, ANALYZE_DIR, DEFAULT_DIR
from mcce_benchmark import Pathok  #: fn
from mcce_benchmark import plots
from mcce_benchmark.scheduling import subprocess_run
import subprocess
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def collate_all_pkas(benchmarks_dir:str, titr_type:str="ph") ->None:
    """Collate all pK.out files from 'benchmarks_dir'/clean_pdbs
       (i.e. assume canonical naming), into a single file
       in 'benchmarks_dir' named as per ALL_PKAS.
       Retain the same fixed-witdth format => extension = ".out".
       This file can be loaded using either one of these functions:
         - pkanalysis.all_pkas_df(benchmarks_dir)
         - pkanalysis.pkout_df(pko_fp, collated=True)
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh']
    """

    bench = Pathok(benchmarks_dir)
    bench_s = str(bench)
    d = Pathok(bench.joinpath(BENCH.CLEAN_PDBS))
    dirpath = str(d)
    all_out = OUT_FILES.ALL_PKAS.value

    titr = titr_type.lower()
    if titr not in ["ph", "eh"]:
        raise ValueError("titr_type must be one of ['ph', 'eh']")

    if titr == "ph":
        titr = "pH"
    else:
        titr = "Eh"

    pko_hdr = f"PDB  resid@{titr}         pKa/Em  n(slope) 1000*chi2      vdw0    vdw1    tors    ebkb    dsol   offset  pHpK0   EhEm0    -TS   residues   total"

    cmd = "awk '{out = substr(FILENAME, length(FILENAME)-10, 4); print out OFS $0}' "
    cmd = cmd + f"{dirpath}/*/pK.out | sed '/total$/d' > {dirpath}/all_pkas; "
    cmd = cmd + f"sed '1 i\{pko_hdr}' {dirpath}/all_pkas > {bench_s}/{all_out};"  # add header back
    cmd = cmd + f" /bin/rm {dirpath}/all_pkas"
    #print(f"cmd = \n{cmd}")

    data = subprocess_run(cmd, capture_output=False) #check=True)
    if isinstance(data, subprocess.CompletedProcess):
        logger.info(f"Created {all_out!r}; Can be loaded using pkanalysis.all_pkas_df(benchmarks_dir).")
    else:
        logger.exception(f"Subprocess error")
        raise data # data holds the error obj
    return


def get_oob_mask(df):
    """Create a mask on df for 'pKa/Em' values out of bound.
    """
    try:
        msk = (abs(df["pKa/Em"]) == 8888.) | (df["pKa/Em"] == 9999.)
        return msk
    except KeyError as e:
        raise e("Wrong dataframe: no 'pKa/Em' columns.")


def extract_oob_pkas(benchmarks_dir:str):
    """Load all_pkas.tsv into df;
    Extract and save out of bound values.
    Rewrite all_pkas.tsv without them.
    """

    # Load all_pkas file, all_pkas.out:
    allout_df = all_pkas_df(benchmarks_dir)
    # convert pK/Em vals to float:
    allout_df["pKa/Em"] = allout_df["pKa/Em"].apply(pk_to_float)

    #extract oob if any
    msk = get_oob_mask(allout_df)
    oob_df = allout_df[msk]
    if oob_df.shape[0]:
        oob_fp = Path(benchmarks_dir).joinpath(ANALYZE_DIR,
                                               OUT_FILES.ALL_PKAS_OOB.value)
        oob_df.to_csv(oob_fp, sep="\t")

        # Reset all_pkas.out
        allout_df = allout_df[~msk]
        all_fp = Path(benchmarks_dir).joinpath(ANALYZE_DIR,
                                               OUT_FILES.ALL_PKAS.value)
        allout_df.to_csv(all_fp, sep="\t")
    else:
        logger.info(f"No out of bound pKa values in {OUT_FILES.ALL_PKAS.value}")

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

    if collated:
        pko_hdr = f"PDB  resid@{titr}         pKa/Em  n(slope) 1000*chi2      vdw0    vdw1    tors    ebkb    dsol   offset  pHpK0   EhEm0    -TS   residues   total"
    else:
        pko_hdr = f" {titr}         pKa/Em  n(slope) 1000*chi2      vdw0    vdw1    tors    ebkb    dsol   offset  pHpK0   EhEm0    -TS   residues   total"
    fields = pko_hdr.strip().split()

    # field width of collated; no space between fields of width 8:
    #line_frmt = "{:<4s} {:<14s}{:9.3f} {:9.3f} {:9.3f}  {:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:8.2f}{:10.2f}"
    fwd_collated = [4, 14, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 10]

    if collated:
        wd = fwd_collated
        flds = fields
    else:
        wd = fwd_collated[1:]
        flds = fields[1:]
        flds.insert(0, f" {titr} ")

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

    return cs, flds


def pk_to_float(value):
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


def all_pkas_df(benchmarks_dir:str, titr_type:str="ph") -> Union[pd.DataFrame, None]:
    """Load <benchmarks_dir>/all_pkas.out into a pandas DataFrame;
    Return  a pandas.DataFrame or None upon failure.
    Version of 'pkanalysis.pkout_df' with pre-set 'all_pkas.out' file
    titr_type (str, 'ph'): titration type, needed for formating; one of ['ph', 'eh']
    """

    d = Pathok(benchmarks_dir, raise_err=False)
    if not d:
        logger.error(f"Not found: {d}")
        return None

    allfp = d.joinpath(OUT_FILES.ALL_PKAS.value)
    if not allfp.exists():
        logger.error(f"Not found: {allfp}; this file is created with pkanalysis.collate_all_pkas(benchmarks_dir).")
        return None

    titr = titr_type.lower()
    if titr not in ["ph", "eh"]:
        raise ValueError("titr_type must be one of ['ph', 'eh']")

    return pkout_df(allfp, collated=True, titr_type=titr)


def all_run_times_to_tsv(pdbs_dir:str, overwrite:bool=False) -> None:
    """Return mcce step times from run.log saved to a tab-separated file.
    """

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

    fp = analyze.joinpath(OUT_FILES.RUN_TIMES.value)
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


def get_step2_count(step2_out_path:str, kind:Union['res', 'confs']) -> int:
    """Return the count of items given by `kind` from a step2_out.pdb file. """

    if kind == "res":
        cmd = "awk '{print $4, substr($5,1,5)}' " + f"{step2_out_path} |uniq|sed -e '/^NTR/d; /^CTR/d'|wc -l"
    elif kind == "confs":
        cmd = "awk '{print $5}' " + f"{step2_out_path} | uniq | wc -l"
    else:
        logger.error(f"kind is one of ['res','confs']; Given: {kind}.")
        raise ValueError(f"kind is one of ['res','confs']; Given: {kind}.")

    data = subprocess_run(cmd)
    if isinstance(data, subprocess.SubprocessError):
        logger.exception(f"Error fetching {kind} count.")
        raise data
    elif not data.stdout.strip():
        logger.info(f"No count from step2_out.pdb in {Path(step2_out_path).parent.name}")
        return 0

    return int(data.stdout.strip())


def all_counts_to_tsv(pdbs_dir:str, kind:Union['res', 'confs'], overwrite:bool=False) -> None:
    """Save the count of items given by `kind` from step2_out.pdb in all subfolders
    of pdbs_dir to a tab-separated file; format: DIR \t n.
    """

    pdbs = Pathok(pdbs_dir)
    # output dir
    analyze = pdbs.parent.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    if kind == "res":
        fname = OUT_FILES.RES_COUNTS.value
    elif kind == "confs":
        fname = OUT_FILES.CONF_COUNTS.value
    else:
        logger.error(f"'kind' must be one of ['res','confs']; Given: {kind}.")
        raise ValueError(f"'kind' must be one of ['res','confs']; Given: {kind}.")

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
    tsv_count = analyze.joinpath(OUT_FILES.CONF_COUNTS.value)
    # res file:
    all_counts_to_tsv(pdbs, kind="res", overwrite=overwrite)
    tsv_res = analyze.joinpath(OUT_FILES.RES_COUNTS.value)

    df_res = pd.read_csv(tsv_res, sep="\t")
    df_res.set_index("PDB", inplace=True)
    df_res.sort_index(inplace=True)

    df_confs = pd.read_csv(tsv_count, sep="\t")
    df_confs.set_index("PDB", inplace=True)
    df_confs.sort_index(inplace=True)

    df = df_confs.merge(df_res, on="PDB")
    df["confs_per_res"] = round(df.confs/df.res,2)

    #final output:
    tsv_fin = analyze.joinpath(OUT_FILES.CONFS_PER_RES.value)
    if tsv_fin.exists() and overwrite:
        tsv_fin.unlink()

    df.to_csv(tsv_fin, sep="\t")

    return


def confs_throughput_to_tsv(pdbs_dir:str, overwrite:bool=False) -> pd.DataFrame:
    """
    Obtain and save the average time & conformer throughput per step in a tab
    separated file, OUT_FILES.CONFS_THRUPUT.
    """

    pdbs = Pathok(pdbs_dir)
    # output dir
    analyze = pdbs.parent.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    # times file:
    tsv_time = analyze.joinpath(OUT_FILES.RUN_TIMES.value)
    if tsv_time.exists() and overwrite:
        tsv_time.unlink()
    all_run_times_to_tsv(pdbs, overwrite=overwrite)

    df_time = pd.read_csv(tsv_time, sep="\t")
    df_time.set_index("PDB", inplace=True)
    df_time.sort_index(inplace=True)

    # confs file:
    tsv_count = analyze.joinpath(OUT_FILES.CONF_COUNTS.value)
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
    tsv_fin = analyze.joinpath(OUT_FILES.CONFS_THRUPUT.value)
    if tsv_fin.exists() and overwrite:
        tsv_fin.unlink()

    gp = df.groupby(by="step", as_index=True).aggregate('mean')
    gp.to_csv(tsv_fin, sep="\t")

    return


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


def pct_completed(book_fpath:str) -> float:
    """Return the pct of runs that are completed."""

    book_fp = Pathok(book_fpath)
    # 2 cmds:
    cmd = f"grep 'c$' {book_fp} |wc -l; cat {book_fp} |wc -l"
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
    Canonical dir struc: book_fpath points to <benchmark_dir>/clean_pdbs/book.txt
    Use: <benchmark_dir>/all_pkas.out
    """

    book_fp = Pathok(book_fpath)
    completed_dirs = get_book_dirs_for_status(book_fp) # default 'c'

    calc_pkas = {}
    # all pkas df: all 'in bound' pk values; floats
    allout_df = all_pkas_df(book_fp.parent.parent)
    c_resid, c_pk = allout_df.columns[:2]

    for dir in completed_dirs:
        pk_df = allout_df.loc[dir]      # filter for this dir
        for r, row in pk_df.iterrows():
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


def match_pkas(expl_pkas:dict, calc_pkas:dict) -> list:
    """Return a list of 3-tuples:
    (id=<pdb>/<res>, experimental pka, calculated pka).
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

        pkas.append(("{}/{}".format(*key), expl_pkas[key], calc_pka))

    return pkas


def matched_pkas_to_csv(benchmarks_dir:str, matched_pkas:list) -> None:
    """Write a list of 3-tuples (as in a matched pkas list) to a csv file."""

    fp = Path(benchmarks_dir).joinpath(ANALYZE_DIR,
                                       OUT_FILES.MATCHED_PKAS.value)
    with open(fp, "w") as fh:
        fh.writelines("key,expl,mcce\n") # header
        fh.writelines("{},{},{}\n".format(*pka) for pka in matched_pkas)

    return


def load_matched_pkas(matched_fp:str) -> pd.DataFrame:
    """
    Load MATCHED_PKA_FILE csv file into a pandas DataFrame.
    PRE: file MATCHED_PKA_FILE csv file created via mcce_benchmark.pkanalysis.
    """

    fh = Path(matched_fp)
    if not fh.exists():
        logger.error(f"Not found: {fh}; run pkanalysis to create.")
        raise FileNotFoundError(f"Not found: {fh}; run pkanalysis to create.")

    df = pd.read_csv(matched_fp)
    df[["PDB", "resid"]] = df.key.str.split("/", expand=True)
    df.drop(columns=["PDB","key"], inplace=True)

    return df[["resid", "expl", "mcce"]]


def matched_pkas_stats(matched_df:pd.DataFrame, prec:int=2) -> dict:
    """Return a dictionnary:
       d_out = {"fit":(m, b),
                "N":N,
                "mean_delta": mean_delta,
                "rmsd":rmsd,
                "bounds":comp_bounds,
                "text":pkas_stats}.
    Save dict as json file: OUT_FILES.MATCHED_PKAS_STATS
    """

    N = matched_df.shape[0]

    m, b = np.polyfit(matched_df.expl, matched_df.mcce, 1)
    delta = abs(matched_df.mcce - matched_df.expl)
    mean_delta = delta.mean(axis=None)
    rmsd = np.sqrt(np.mean(delta**2))

    txt = f"""Residues stats:
Number of pKas matched with those in pKaDB: {N:,}
Fit line: y = {m:.{prec}f}.x + {b:.{prec}f}
Mean delta pKa: {mean_delta:.{prec}f}
RMSD, calculated vs experimental: {rmsd:.{prec}f}
"""

    comp_bounds = [3., 2., 1.]
    for b in comp_bounds:
        txt = txt + f"Proportion within {b} pH units: {delta[delta.le(b)].count()/N:.{prec}%}\n"

    d_out = {"fit":(m, b),
             "N":N,
             "mean_delta": mean_delta,
             "rmsd":rmsd,
             "bounds":comp_bounds,
             "txt":txt}

    # TODO: save dict to json:
    
    return d_out


def res_outlier_count(matched_fp:str, replace=False) -> tuple:
    """Return counts per residue type for diff(mcce-expl) > 3,
    and pKa values beyond titration bounds in text and df format.
    Save text to "outlier_residues.tsv" (OUT_FILES.RES_OUTLIER).
    ASSUMED: bounds=(0,14)
    """

    matched_df = load_matched_pkas(matched_fp)
    matched_df[["res", "resi"]] = matched_df.resid.str.split("[-|+]", expand=True)
    matched_df.drop(columns=["resi", "resid"], inplace=True)
    matched_df["delta"] = abs(matched_df.mcce - matched_df.expl)
    matched_df["Delta over 3"] = matched_df.delta > 3.0
    matched_df["Out of bounds"] = (abs(matched_df.mcce) < 0.01) | (abs(matched_df.mcce - 14.0) < 0.01)
    matched_df.drop(columns=["expl", "mcce", "delta"], inplace=True)

    gp_oob = matched_df[matched_df["Out of bounds"]==True].groupby("res").count()
    gp_oob.drop(columns="Delta over 3", inplace=True)
    gp_del3 = matched_df[matched_df["Delta over 3"]==True].groupby("res").count()
    gp_del3.drop(columns="Out of bounds", inplace=True)
    out_df = gp_del3.merge(gp_oob, how='left', on="res").replace({np.nan:0}).astype(int)
    out_df.index.name = None

    outlier_fp = Path(matched_fp).parent.joinpath(OUT_FILES.RES_OUTLIER.value)
    if outlier_fp.exists() and replace:
        outlier_fp.unlink()
    out_df.to_csv(outlier_fp, sep="\t")
    
    return out_df


def analyze_expl_pkas(benchmarks_dir:Path):
    """Create all analysis output files."""

    bench_dir = Path(benchmarks_dir)
    pdbs = bench_dir.joinpath(BENCH.CLEAN_PDBS)
    book_fp = pdbs.joinpath(BENCH.Q_BOOK)

    analyze = bench_dir.joinpath(ANALYZE_DIR)
    if not analyze.exists():
        analyze.mkdir()

    logger.info(f"Collating all completed pK.out files.")
    collate_all_pkas(bench_dir)

    logger.info(f"Saving out of bounds pK values to tsv, if any.")
    extract_oob_pkas(bench_dir)

    logger.info(f"Calculating conformers and residues counts into tsv files.")
    all_counts_to_tsv(pdbs, kind="confs", overwrite=True)
    all_counts_to_tsv(pdbs, kind="res", overwrite=True)
    all_run_times_to_tsv(pdbs, overwrite=True)
    confs_per_res_to_tsv(pdbs)

    logger.info(f"Calculating conformers thoughput into tsv files.")
    confs_throughput_to_tsv(pdbs)

    logger.info(f"Loading the experimental and calculated pKas to dict.")
    expl_pkas = experimental_pkas_to_dict()
    calc_pkas = job_pkas_to_dict(book_fp)

    logger.info(f"Matching the pkas and saving list to csv file.")
    matched_pKas = match_pkas(expl_pkas, calc_pkas)
    matched_pkas_to_csv(bench_dir, matched_pKas)

    logger.info(f"Calculating the matched pkas stats into dict.")
    matched_fp = analyze.joinpath(OUT_FILES.MATCHED_PKAS.value)
    matched_df = load_matched_pkas(matched_fp)
    #TODO: save stats to file
    d_stats = matched_pkas_stats(matched_df)
    # no need for returned df here -> to tsv:
    _ = res_outlier_count(matched_fp)

    #plots
    logger.info(f"Plotting conformers throughput per step -> pic.")
    tsv = matched_fp.parent.joinpath(OUT_FILES.CONFS_THRUPUT.value)
    thruput_df = load_tsv(tsv, index_col="step")
    save_to = matched_fp.parent.joinpath(OUT_FILES.CONFS_TP_PNG.value)
    plots.plot_conf_thrup(thruput_df, save_to)

    logger.info(f"Plotting pkas fit -> pic.")
    save_to = matched_fp.parent.joinpath("pkas_fit")
    plots.plot_pkas_fit(matched_df, d_stats, save_to)

    logger.info(f"Plotting residues analysis -> pic.")
    save_to = matched_fp.parent.joinpath("res_analysis")
    plots.plot_res_analysis(matched_pKas, save_to)

    return

#................................................................................
def expl_pkas_comparison(args:argNamespace):
    """Processing tied to sub-command 'expl_pkas'."""

    

    return


#........................................................................
CLI_NAME = ENTRY_POINTS["analyze"] # as per pyproject.toml entry point

SUB_CMD1 = "expl_pkas"
HELP_1 = """Sub-command for analyzing a benchmarking job against the pKaDBv1
using the same dataset and structure: <benchmarks_dir>/clean_pdbs folder."
"""

#SUB_CMD2 = "mcce_runs"
#HELP_2 = "NOT YET IMPLEMENTED."
#- Sub-command 2: {SUB_CMD2!r}: setup the run script to run mcce steps 1 through 4;


DESC = f"""
Description:
Analyze the pkas from a set of mcce calculations run over the pKa DBv1 dataset.

The main command is {CLI_NAME!r} along with one of 2 sub-commands:
- Sub-command 1: {SUB_CMD1!r}: analyze pKas against pKaDBv1;

Post an issue for all errors and feature requests at:
https://github.com/GunnerLab/MCCE_Benchmarking/issues
"""

USAGE = f"""
{CLI_NAME} <+ sub-command :: one of [{SUB_CMD1}]> <related args>\n
PURPOSE: Collate all pK.out files into one in <benchmarks_dir>;
         Create all necessary files and pictures for report building
         in <benchmarks_dir>/analysis/.

Examples for current implementation (Beta):
 - Using defaults (benchmarks_dir={DEFAULT_DIR}, min_pct_complete=100):
   >{CLI_NAME} {SUB_CMD1}

 - Using non-default values:
   >{CLI_NAME} {SUB_CMD1} -benchmarks_dir <different name> -min_pct_complete 0.9
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
        usage = USAGE,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = ">>> END of %(prog)s",
    )

    subparsers = p.add_subparsers(required = True,
                                  title = f"{CLI_NAME} sub-commands",
                                  dest = "subparser_name",
                                  description = "Sub-commands of MCCE benchmarking analysis cli.",
                                  help = f"""The 2 choices for the benchmarking process:
                                  1) Analyze dataset of mcce runs viz pKaDBv1: {SUB_CMD1}
                                  2) FUTURE: Analyze two mcce runs
                                  """)

    sub1 = subparsers.add_parser(SUB_CMD1,
                                 formatter_class = RawDescriptionHelpFormatter,
                                 help=HELP_1)
    sub1.add_argument(
        "-benchmarks_dir",
        default = str(Path(DEFAULT_DIR).resolve()),
        type = arg_valid_dirpath,
        help = """The user's directory where the "clean_pdbs" folder reside; default: %(default)s.
        """
    )
    sub1.set_defaults(func=expl_pkas_comparison)

    return p


def analyze_cli(argv=None):
    """
    Command line interface for MCCE benchmarking analysis entry point.
    """

    cli_parser = analyze_parser()

    if argv is None or len(argv) <= 1:
        cli_parser.print_usage()
        return

    if '-h' in argv or '--help' in argv:
        cli_parser.print_help()
        return

    args = cli_parser.parse_args(argv)

    # OK to analyze?
    bench_dir = Pathok(args.benchmarks_dir)
    book_fp = bench_dir.joinpath(BENCH.CLEAN_PDBS, BENCH.Q_BOOK)
    pct = pct_completed(book_fp)
    if pct < 1.:
        logger.info(f"Runs not 100% complete; completed = {pct:.2f}")
        return

    args.func(args)

    return


if __name__ == "__main__":

    analyze_cli(sys.argv[1:])
