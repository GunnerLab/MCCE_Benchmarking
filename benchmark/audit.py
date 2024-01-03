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


DATA = Path(__file__).parent.joinpath("data")
PDBS = DATA.joinpath("clean_pdbs")
WT = DATA.joinpath("WT_pkas.csv")
Q_BOOK = DATA.joinpath("book.txt")
PROTS = DATA.joinpath("proteins.txt")


MCCE_OUTPUTS = ["acc.atm", "acc.res", "entropy.out", "fort.38",
                "head1.lst", "head2.lst", "head3.lst", "mc_out",
                "pK.out", "prot.pdb", "respair.lst", "rot_stat", "run.log", "run.prm", "run.prm.record",
                "step0_out.pdb", "step1_out.pdb", "step2_out.pdb", "step3_out.pdb",
                "sum_crg.out", "vdw0.lst", "null", "new.tpl"]
# dir: "energies", "param", "ms_out": automatically deleted


def delete_mcce_outputs(mcce_dir:str) -> None:
    """Delete all MCCE output files or folder from a MCCE run folder."""
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


def clean_job_folder(pdbs_dir: str) -> None:
    """Delete all MCCE output files and folders from the directory `pdbs_dir`,
    which is a folder of folder named after the pdb id they contain."""

    pdbs = Path(pdbs_dir)
    for fp in pdbs.iterdir():
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


def pdb_list_from_proteins(prot_file:str) -> list:

    parsed = []
    skipped = []
    with open(Path(prot_file)) as p:
        for i, line in enumerate(p):
            if i == 0:
                continue
            if line.startswith("#"):
                skipped.append(f"Commented {i}: {line}")
                continue
            fields = line.split(maxsplit=1)
            parsed.append(fields[0])

    return parsed, skipped


def pdb_list_from_book(book_file:str) -> list:

    pdbs = []
    with open(Path(book_file)) as book:
        for line in book:
            rawtxt = line.strip().split("#")[0]
            pdbs.append(rawtxt.split()[0])

    return pdbs


def pdb_list_from_clean_pdbs_folder(clean_dir:str) -> list:
    """clean_dir: folder with one PDBID folder for each pdbid.pdb file"""

    clean_pdbs_dirs = [fp.name for fp in Path(clean_dir).glob('*') if fp.is_dir() and not fp.name.startswith(".")]
    clean_pdbs_dirs.sort()

    return clean_pdbs_dirs


def audit_clean_pdbs_folder(clean_pdbs_dir:str) -> tuple:
    """Check that all subfolders contain a pdb file with the same name.
    Return a 2-tuple: (valid_folders, invalid_folders).
    """
    pdbs_dir = Path(clean_pdbs_dir)
    if not pdbs_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {pdbs_dir}")

    valid = []
    invalid = []
    for fp in pdbs_dir.glob('*'):
        if fp.is_dir() and not fp.name.startswith("."):
            if fp.joinpath(f"{fp.name.lower()}.pdb").exists():
                valid.append(fp.name)
            else:
                invalid.append(fp.name)
    valid.sort()
    invalid.sort()
    print(f"Valid folders: {len(valid)}; Invalid folders: {len(invalid)}")

    return valid, invalid


def reset_book_file(book_file:str) -> None:
    """Re-write clean_pdbs/book file with valid entries."""

    book_fp = Path(book_file)
    valid, invalid = audit_clean_pdbs_folder(book_fp.parent)
    with open(book_fp, "w") as book:
        book.writelines([f"{v}\n" for v in valid])
    return


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
