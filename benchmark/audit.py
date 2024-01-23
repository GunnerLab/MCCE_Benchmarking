"""Module: audit.py
Contains functions to query and manage data.
"""

# import class of files resources and constants:
from benchmark import APP_NAME, BENCH, MCCE_OUTPUTS
from functools import cache
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import subprocess
from typing import Union


MULTI_ACTIVE_MSG = \
"""Multi-model folder {!r} contains multiple 'active' pdbs with
{!r} being the second one.
The only 'active' pdb (to be selected as 'prot.pdb'), must be the one
listed in the 'Use' colummn in the 'proteins.tsv' file.
The function audit.reset_multi_models() must be re-run to fix the problem.
"""

logger = logging.getLogger(f"{APP_NAME}.{__name__}")
logger.setLevel(logging.DEBUG)


def proteins_df(prot_tsv_file:Path = BENCH.BENCH_PROTS, return_excluded:bool = False) -> pd.DataFrame:
    """
    Load data/proteins.tsv into a pandas.DataFrame.
    """
    df = pd.read_csv(prot_tsv_file, sep="\t")
    df.sort_values(by="PDB", inplace=True)
    if return_excluded:
        return df[df.Use.isna()]
    return df


def valid_pdb(pdb_dir:Path, return_name:bool = False) -> Union[bool, Path, None]:
    """Return whether 'pdb_dir' contains a valid pdb (default), or its name if
    'return_name'=True if valid, else None.
    Used by list_all_valid_pdbs.
    """

    # single model pdb
    pdb = pdb_dir.joinpath(f"{pdb_dir.name.lower()}.pdb")
    ok = pdb.exists()
    if ok: # found
        if return_name:
            return pdb
        else:
            return ok

    # multi-model protein: main pdb was renamed with .full extension
    files = [fp for fp in pdb_dir.glob("*.[pdb full]*") if not fp.name.startswith("model")]
    found_full = False
    found_active = False
    active = []
    for f in files:
        if f.suffix == ".full":
            found_full = True
            continue
        if f.name.startswith(f"{pdb_dir.name.lower()}_"):
            found_active = True
            if return_name:
                pdb = f
            # to check if several are 'valid'
            active.append(True)
            if len(active) > 1:
                #-> log
                print(MULTI_ACTIVE_MSG.format(pdb_dir.name, f.name))
                found_active = False
                break

    # FIX: 'and' => will fail if all multi prots are removed:
    valid = found_full and found_active
    if return_name:
        if not valid:
            return None
        return pdb
    else:
        return valid


@cache
def list_all_valid_pdbs(clean_pdbs_dir:Path = BENCH.BENCH_PDBS) -> tuple:
    """Return a list ["PDB/pdb[_*].pdb", ] of valid pdb.
    Return a 2-tuple: (valid_folders, invalid_folders).
    For managing packaged data.
    """
    if not clean_pdbs_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {clean_pdbs_dir}")

    valid = []
    invalid = []
    for fp in clean_pdbs_dir.glob("*"):
        if fp.is_dir() and not fp.name.startswith("."):
            p = valid_pdb(fp, return_name=True)
            if p is None:
                invalid.append(fp.name)
            else:
                valid.append(f"{fp.name}/{p.name}")
    valid.sort()
    invalid.sort()
    print(f"\tValid pdbs: {len(valid)}; Invalid pdbs: {len(invalid)}")
    if len(invalid):
        print(f"\tInvalid pdbs: {invalid}")

    return valid, invalid


@cache
def list_all_valid_pdbs_dirs(clean_pdbs_dir:Path = BENCH.BENCH_PDBS) -> tuple:
    """Check that all subfolders of 'clean_pdbs_dir' contain a pdb file with
    the same name.
    Return a 2-tuple: (valid_folders, invalid_folders).
    For managing packaged data.
    """

    if not clean_pdbs_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {clean_pdbs_dir}")

    valid = []
    invalid = []
    for fp in clean_pdbs_dir.glob("*"):
        if fp.is_dir() and not fp.name.startswith("."):
            v = valid_pdb(fp)
            if v:
                valid.append(fp.name)
            else:
                invalid.append(fp.name)
    valid.sort()
    invalid.sort()
    logger.info(f"list_all_valid_pdbs_dirs :: Valid folders: {len(valid)}; Invalid folders: {len(invalid)}")

    return valid, invalid


def multi_model_pdbs(clean_pdbs_dir:Path = BENCH.BENCH_PDBS) -> Union[np.ndarray, None]:
    """
    Query `clean_pdbs_dir` for pdb with multiple models.
    Return dir/pdb name in a numpy array or None.
    """

    multi_models = None
    pdbs_query_path = clean_pdbs_dir.joinpath("*/")
    n_parts = len(pdbs_query_path.parts) + 2
    f1 = n_parts - 2
    f2 = n_parts - 1
    print_fields = "{print $" + str(f1) + '","$' + str(f2) + "}"
    cmd = f"grep '^MODEL' {pdbs_query_path}/*.pdb | sed -e '/model/d; s/:MODEL/\//g'|gawk -F'/|:' '{print_fields}' | uniq"

    data = subprocess.check_output(cmd,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   shell=True
                                   ).splitlines()
    if data:
        multi_models = np.array([line.split(",") for line in data])

    return multi_models


def reset_multi_models(pdbs_dir:Path = BENCH.BENCH_PDBS, debug:bool = False) -> list:
    """Use multi model entries in 'data/proteins.tsv' to select the
    model<x>.pdbs corresponding to the proteins 'Use' column, if found.

    Rename pdbid.pdb -> pdbid.pdb.full
    n = matched model number from Use.split(".")[1]
    new_n = Use.replace(".",'')
    Rename model{n:02}.pdb -> pdbid_{new_n}.pdb

    Should be re-run every time the 'Use' column in 'data/proteins.tsv' is
    changed for one or more multi-model proteins.
    For managing packaged data.
    """
    prots_df = proteins_df()
    multi = prots_df[prots_df.Model == 'multi']

    missing_data = []

    for i, ro in multi.iterrows():
        pdb = ro.PDB.lower()
        chain, n = ro.Use.split(".")
        n = int(n.strip())

        mdir = pdbs_dir.joinpath(ro.PDB)
        pdb_path = mdir.joinpath(f"{pdb}.pdb")
        path_full = mdir.joinpath(f"{pdb}.pdb.full")
        use_prot = mdir.joinpath(f"{pdb}_{chain}{n}.pdb")
        modl_prot = mdir.joinpath(f"model{n:02}.pdb")

        if path_full.exists():
            # possibly already processed, check if protein in use matches:
            if use_prot.exists():
                # matched, done:
                continue
            #else, check the model pdb
            if not modl_prot.exists():
                print("Could not find {modl_prot} to rename as {use_prot}.")
                missing_data.append(modl_prot)
                continue

            # rename previously used prots:
            pdb_glob = f"{mdir.name.lower()}_*.pdb"
            used_prots = list(mdir.glob(pdb_glob))
            if used_prots:
                for p in used_prots:
                    if debug:
                        print(f"shutil.move({p}, {p}.x)")
                    else:
                        _ = shutil.move(p, f"{p}.x")

            if debug:
                print(f"shutil.copy({modl_prot}, {use_prot})")
            else:
                _ = shutil.copy(modl_prot, use_prot)

        else:
            if not pdb_path.exists():
                print("Expected pdb not found: {pdb_path}.")
                missing_data.append(pdb_path)
                continue
            if debug:
                print(f"shutil.move({pdb_path}, {path_full})")
            else:
                _ = shutil.move(pdb_path, path_full)

            if not modl_prot.exists():
                print("Could not find {modl_prot} to rename as {use_prot}.")
                missing_data.append(modl_prot)
                continue

    return missing_data


def update_proteins_multi(proteins_file:Path = BENCH.BENCH_PROTS):
    """Update 'data/proteins.tsv' Model column from
    list of multi-model proteins.
    For managing packaged data.
    """

    multi_models = multi_model_pdbs()
    if multi_models is None:
        print("No multi model pdbs.")
        return

    prots_df = proteins_df(proteins_file)
    for pdb in multi_models[:,0]:
        try:
            prots_df.loc[prots_df.PDB == pdb, "Model"] = "multi"
        except:
            continue

    prots_df.to_csv(BENCH.BENCH_PROTS, index=False, sep="\t")

    return


def rewrite_book_file(book_file:Path) -> None:
    """Re-write clean_pdbs/book file with valid entries."""

    valid, invalid = list_all_valid_pdbs_dirs(book_file.parent)
    with open(book_file, "w") as book:
        book.writelines([f"{v}\n" for v in valid])
    return


def pdb_list_from_book(book_file:Path = Path(BENCH.Q_BOOK)) -> list:

    pdbs = []
    with open(book_file) as book:
        for line in book:
            rawtxt = line.strip().split("#")[0]
            pdbs.append(rawtxt.split()[0])

    return pdbs


def pdb_list_from_clean_pdbs_folder(clean_pdbs_dir:Path = BENCH.BENCH_PDBS) -> list:
    """clean_dir: folder with one PDBID folder for each pdbid.pdb file"""

    clean_pdbs_dirs = [fp.name for fp in clean_pdbs_dir.glob('*')
                       if fp.is_dir()
                       and not fp.name.startswith(".")]
    clean_pdbs_dirs.sort()

    return clean_pdbs_dirs


def same_pdbs_book_vs_clean() -> bool:
    """
    Compares the list of pdbs in the Q_BOOK with the list
    obtained from the PDBS folder.
    For managing packaged data.
    """
    book_pbs =  pdb_list_from_book()
    clean_pdbs = pdb_list_from_clean_pdbs_folder()
    same = len(book_pbs) == len(clean_pdbs)
    if not same:
        print("The lists differ in lengths:",
              f"{len(book_pbs) = }; {len(clean_pdbs) = }")
        return same

    df = pd.DataFrame(zip(book_pbs, clean_pdbs), columns=['book','clean_dir'])
    comp = df[df.book != df.clean_dir]
    same = len(comp) == 0
    if not same:
        print(f"The lists differ in data:\n{comp}")

    return same


def to_float(value):
    """Conversion function to be used in pd.read_csv.
    Return NA on conversion failure.
    """
    try:
        new = float(value)
    except:
        new = np.nan

    return new


def pdb_list_from_experimental_pkas(pkas_file:str) -> list:
    """Parses valid pKa values from an experiemntal pKa file and return
    their pdb ids in a list."""

    fp = Path(pkas_file)
    if fp.name != "WT_pkas.csv":
        raise TypeError("Only wild type proteins listed in 'WT_pkas.csv' are currently considered.")

    pkas_df = pd.read_csv(fp,
                          usecols=["PDB ID", "Expt. pKa"],
                          comment="#",
                          converters={"Expt. pKa": to_float},
                          ).dropna(how="any")

    pdbs = pkas_df['PDB ID'].unique().tolist()
    pdbs.sort()

    return pdbs


##############################################################
# transformation of legacy files

def proteins_to_tsv(prot_file:str) -> list:
    """Transform initial text file to a tab separated file (.tsv)
    with additional column 'Model' to indicate whether pdb is single- or
    multi-modelled. No duplicates.
    """

    prots = Path(prot_file)
    tsv = prots.parent.joinpath("proteins.tsv")
    uniq = []
    with open(prots) as p, open(tsv, "w") as out:
        for i, line in enumerate(p):
            if i == 0:
                out.write("\t".join(line.split()) + "\tModel\n")
                continue

            pdb, fields = line.split("   ", maxsplit=1)
            if pdb not in uniq:
                uniq.append(pdb)
                if line.startswith("#"):
                    out.write(f"{pdb}\t{fields.strip()}\t\t\n")
                else:
                    other = fields.split("   ", maxsplit=1)
                    out.write(f"{pdb}\t{other[0].strip()}\t{other[1].strip()}\tsingle\n")
    return
