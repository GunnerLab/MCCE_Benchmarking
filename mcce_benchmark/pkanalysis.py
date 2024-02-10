#!/usr/bin/env python

"""
Uses the legacy implementation usage:
USAGE: to be run in the user's 'mcce_benchmarks' folder (defaults name).
Example. Assuming your at you home directory (cd ~):
> cd path/to/<mcce_benchmarks>
> python pkanalysis.py
"""

from mcce_benchmark import BENCH, MATCHED_PKAS_FILE
from mcce_benchmark.scheduling import subprocess_run
import logging
import numpy as np
import pandas
from pathlib import Path


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_conf_count() -> int:
    """Get the number of conformers in step3_out.pdb."""

    #awk '{print $5}' step3_out.pdb |uniq|wc -l


def get_book_dirs_for_status(book_fp:str, status:str="c") -> list
    """Return a list of folder names from book_fp, the Q_BOOK file path,
    if their status codes match 'status', i.e. completed ('c', default),
    or errorneous ('e').
    """

    status = status.lower()
    if not status or status not in ["c", "e"]:
        logger.error("Invalid 'status'; choices are 'c' or 'e'")
        raise ValueError("Invalid 'status'; choices are 'c' or 'e'")

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


def job_pkas_to_dict(book_file:str = BENCH.Q_BOOK) -> dict:
    """
    Uses the 'q-book' file to retrieve completed jobs and their respective pK.out file.
    Origin: pkanalysis.py/read_calculated_pkas
    """

    book_fp = Path.cwd().joinpath(book_file)
    if not book_fp.exists():
        logger.error(f"File not found: {book_fp}")
        raise FileNotFoundError(f"File path: {book_fp}")

    completed_dirs = get_book_dirs_for_status(book_fp) # default 'c'

    calc_pkas = {}
    for dir in completed_dirs:
        # read residues' pKas in pK.out:
        lines = open(book_fp.parent.joinpath(dir, "pK.out")).readlines()
        lines.pop(0)  # header
        for line in lines:
            fields = line.split()
            if len(fields) >= 2:
                try:
                    pka = float(fields[1])
                except:
                    continue

                key = (dir, fields[0])
                if key[:3] == "NTG":
                    key = "NTR" + key[3:]
                calc_pkas[key] = pka

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


def experimental_pkas_to_dict(pkas_file:str=BENCH.BENCH_WT.name, ) -> dict:
    """Origin: pkanalysis.py/read_experiment_pkas
    """

    if pkas_file != "WT_pkas.csv":
        logger.error(f"Only wild type proteins listed in {BENCH.BENCH_WT.name!r} are currently considered.")
        raise TypeError(f"Only wild type proteins listed in {BENCH.BENCH_WT.name!r} are currently considered.")

    exp_pka_fp = Path.cwd().joinpath(pkas_file)
    if not exp_pka_fp.exists():
        logger.error(f"File not found: {exp_pka_fp}")
        raise FileNotFoundError(f"File path: {exp_pka_fp}")

    res_to_mcce = {"ARG": "ARG+",
                   "HIS": "HIS+",
                   "LYS": "LYS+",
                   "N-TERM": "NTR+",
                   "ASP": "ASP-",
                   "GLU": "GLU-",
                   "C-TERM": "CTR-",
                   "CYS": "CYS-",
                   "TYR": "TYR-"}

    pkas_df = pd.read_csv(exp_pka_fp,
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

    #calculated_ids = []
    #for key in calc_pkas:
    #    if key[0] not in calculated_ids:
    #        calculated_ids.append(key[0])

    calculated_ids = list(set([key[0] for key in calc_pkas]))
    print(f"{calculated_ids = }") # temp

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

        #pka = ("{}/{}".format(*key), expl_pkas[key], calc_pka)
        pkas.append(("{}/{}".format(*key), expl_pkas[key], calc_pka))

    return pkas


def matched_pkas_to_csv(matched_pkas:list, file_path:str=MATCHED_PKAS_FILE) -> None:
    """Write a list of 3-tuples (as in a matched pkas list) to a comma separated file."""

    fp = Path.cwd().joinpath(file_path)
    if fp.exists():
        logger.error(f"File {fp!r} already exists: either delete or rename it before saving.")
        raise FileExistsError(f"File {fp!r} already exists: either delete or rename it before saving.")

    if fp.suffix !=".csv":
        fp = fp.parent.joinpath(f"{fp.stem}.csv")

    with open(fp, "w") as fh:
        fh.writelines("{}, {}, {}\n".format(*pka) for pka in matched_pkas)

    return


def expl_pka_comparison():
    #TODO: Get run times

    calc_pkas = job_pkas_to_dict()
    expl_pkas = experimental_pkas_to_dict()
    matched_pKas = match_pkas(expl_pkas, calc_pkas)
    matched_pkas_to_csv(matched_pKas, fname=MATCHED_PKAS_FILE)

    n = len(matched_pKas)

    # Overall fitting
    x = np.array([p[1] for p in matched_pKas])
    y = np.array([p[2] for p in matched_pKas])

    delta = np.abs(x-y)
    m, b = np.polyfit(x, y, 1)
    rmsd = np.sqrt(np.mean((x-y)**2))

    within_1, within_2 = 0, 0
    for d in delta:
        if d <= 2.0:
            within_2 += 1
            if d <= 1.0:
                within_1 += 1

    print(f"Fit line: y = {m:.2f}.x + {b:.2f}")
    print(f"RMSD between calculated and exprimental: {rmsd:.2f}")
    print(f"Proportion within 2 pH units: {within_2/n:.1%}")
    print(f"Proportion within 1 pH unit: {within_1/n:.1%}")

    #
    # plt.plot(x, y, 'o')
    # plt.plot(x, b + m * x, '-', color="k")
    # plt.plot(x, b+1 + m * x, '--', color="y")
    # plt.plot(x, b-1 + m * x, '--', color="y")
    # plt.plot(x, b+2 + m * x, ':', color="r")
    # plt.plot(x, b-2 + m * x, ':', color="r")
    # plt.show()
    #
    # # Individual residue analysis
    # residues_stat = {}
    # for pka in matched_pKas:
    #     resname = pka[0][5:8]
    #     expr_pka = pka[1]
    #     calc_pka = pka[2]
    #     if resname in residues_stat:
    #         residues_stat[resname].append(pka)
    #     else:
    #         residues_stat[resname] = [pka]
    #
    # #print(list(residues_stat.keys()))
    # for key in residues_stat:
    #     x = np.array([p[1] for p in residues_stat[key]])
    #     y = np.array([p[2] for p in residues_stat[key]])
    #     m, b = np.polyfit(x, y, 1)
    #     plt.plot(x, y, "o")
    #     plt.plot(x, m * x + b, '-', color="k")
    #     plt.title(key)
    #     plt.show()
    #
    # # Outlier case analysis
    # for pka in matched_pKas:
    #     id = pka[0]
    #     if abs(pka[2]) < 0.01 or abs(pka[2] - 14.0) < 0.01:
    #         print(id, "%.3f %.3f" % (pka[1], pka[2]))
    #     elif abs(pka[1] - pka[2]) > 2.0:
    #         print(id, "%.3f %.3f" % (pka[1], pka[2]))


if __name__ == "__main__":
    main()
