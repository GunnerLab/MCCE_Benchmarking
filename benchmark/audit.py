"""Module: audit.py

The numbers do not match (12/28/2023):
```
pdbs_proteins, pdbs_skipped = audit.pdb_list_from_proteins(PROTS)
print(f"Validated proteins from {PROTS.name!r}: {len(pdbs_proteins)}; skipped: {len(pdbs_skipped)}")

expl_pdbs = audit.pdb_list_from_experimental_pkas(WT)
print(f"Proteins from {WT.name!r}: {len(expl_pdbs)}")

book_pdbs = audit.pdb_list_from_book(Q_BOOK)
print(f"Proteins from {Q_BOOK.name!r}: {len(book_pdbs)}")

clean_pdbs = audit.pdb_list_from_clean_pdbs_folder(PDBS, use_old=True)
print(f"Proteins from {PDBS.name!r} folder: {len(clean_pdbs)}")

>>Validated proteins from 'proteins': 124; skipped: 35
>>Proteins from 'WT_pkas.csv': 150
>>Proteins from 'book': 126
>>Proteins from 'clean_pdbs' folder: 139
```
"""

import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import subprocess
from typing import Union


DATA = Path(__file__).parent.joinpath("data")
WT = DATA.joinpath("WT_pkas.csv")
PROTS = DATA.joinpath("proteins.tsv")
PDBS = DATA.joinpath("clean_pdbs")
Q_BOOK = PDBS.joinpath("book.txt")


def proteins_df(prot_tsv_file:Path = PROTS, return_excluded:bool = False) -> pd.DataFrame:
    """
    Load data/proteins.tsv into a pandas.DataFrame.
    """
    df = pd.read_csv(prot_tsv_file, sep="\t")
    df.sort_values(by="PDB", inplace=True)
    if return_excluded:
        return df[df.Use.isna()]
    return df


def multi_model_pdbs(clean_pdbs_dir:Path = PDBS) -> Union[np.ndarray, None]:
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


def reset_multi_models(pdbs_dir:Path = PDBS, debug:bool = False) -> list:
    """Use multi model entries in 'data/proteins.tsv' to select the
    model<x>.pdbs corresponding to the proteins 'Use' column, if found.

    Rename pdbid.pdb -> pdbid.pdb.full
    n = matched model number from Use.split(".")[1]
    new_n = Use.replace(".",'')
    Rename model{n:02}.pdb -> pdbid_{new_n}.pdb

    Should be re-run every time the 'Use' column in 'data/proteins.tsv' is
    changed for one or more multi-model proteins.
    """
    prots_df = proteins_df(PROTS)
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
            pdb_glob = f"{mdir.name.lower()}*.pdb"
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


def update_proteins_multi(proteins_file:Path = PROTS):
    """Update 'data/proteins.tsv' Model column from
    list of multi-model proteins."""

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

    prots_df.to_csv(PROTS, index=False, sep="\t")

    return


MCCE_OUTPUTS = ["acc.atm", "acc.res", "entropy.out", "fort.38",
                "head1.lst", "head2.lst", "head3.lst", "mc_out",
                "pK.out", "prot.pdb", "respair.lst", "rot_stat", "run.log", "run.prm", "run.prm.record",
                "step0_out.pdb", "step1_out.pdb", "step2_out.pdb", "step3_out.pdb",
                "sum_crg.out", "vdw0.lst", "null", "new.tpl"]


def delete_mcce_outputs(mcce_dir:str) -> None:
    """Delete all MCCE output files or folders from a MCCE run folder.
    Note: All subfolders within `mcce_dir` are automatically deleted.
    """

    folder = Path(mcce_dir)
    if not folder.is_dir():
        print(f"{folder = } does not exist.")
        return

    for fp in folder.iterdir():
        if fp.is_dir():
            shutil.rmtree(fp)
        else:
            if fp.name in MCCE_OUTPUTS:
                fp.unlink()

    return


def clean_job_folder(job_dir:str) -> None:
    """Delete all MCCE output files and folders from a directory `job_dir`,
    which is a folder of folder named after the pdb id they contain.
    """
    pdbs_dir = Path(job_dir)
    for fp in pdbs_dir.iterdir():
        if fp.is_dir():
            delete_mcce_outputs(fp)
        else:
            print(f"{fp = }: remaining")

    return


def to_float(value):
    """Conversion function to be used in pd.read_csv.
    Return NA on conversion failure.
    """
    try:
        new = float(value)
    except:
        new = np.nan

    return new


def reset_book_file(book_file:Path = Q_BOOK) -> None:
    """Re-write clean_pdbs/book file with valid entries."""

    valid, invalid = audit_clean_pdbs_folder(book_file.parent)
    with open(book_file, "w") as book:
        book.writelines([f"{v}\n" for v in valid])
    return


def pdb_list_from_book(book_file:Path = Q_BOOK) -> list:

    pdbs = []
    with open(book_file) as book:
        for line in book:
            rawtxt = line.strip().split("#")[0]
            pdbs.append(rawtxt.split()[0])

    return pdbs


def pdb_list_from_clean_pdbs_folder(clean_pdbs_dir:Path = PDBS) -> list:
    """clean_dir: folder with one PDBID folder for each pdbid.pdb file"""

    clean_pdbs_dirs = [fp.name for fp in clean_pdbs_dir.glob('*')
                       if fp.is_dir()
                       and not fp.name.startswith(".")]
    clean_pdbs_dirs.sort()

    return clean_pdbs_dirs


def same_pdbs_book_v_clean() -> bool:
    """
    Compares the list of pdbs in the Q_BOOK with the list
    obtained from the PDBS folder.
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


def audit_clean_pdbs_folder(clean_pdbs_dir:Path = PDBS) -> tuple:
    """Check that all subfolders contain a pdb file with the same name.
    Return a 2-tuple: (valid_folders, invalid_folders).
    """

    if not clean_pdbs_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {clean_pdbs_dir}")

    valid = []
    invalid = []
    for fp in clean_pdbs_dir.glob('*'):
        if fp.is_dir() and not fp.name.startswith("."):
            if (fp.joinpath(f"{fp.name.lower()}.pdb").exists()
                or fp.joinpath(f"{fp.name.lower()}.pdb.full").exists()):
                valid.append(fp.name)
            else:
                invalid.append(fp.name)
    valid.sort()
    invalid.sort()
    print(f"Valid folders: {len(valid)}; Invalid folders: {len(invalid)}")

    return valid, invalid


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
