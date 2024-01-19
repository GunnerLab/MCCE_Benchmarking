#!/usr/bin/env python
from pathlib import Path
import pandas
import numpy as np
"""
TODO: Check fns with file path as input
"""

def job_pkas_to_dict(book_file:str) -> dict:
    """
    Uses the 'book' file to retrieve completed jobs and their respective pK.out file.
    Origin: pkanalysis.py/read_calculated_pkas
    """

    completed_dirs = []
    book_fp = Path(book_file)
    with open(book_fp) as book:
        for line in book:
            # select only the portion preceding any appended comment
            rawtxt = line.strip().split("#")[0]
            fields = rawtxt.split()
            if len(fields) == 2:
                if fields[1].lower() == "c":
                    completed_dirs.append(fields[0])

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


def experimental_pkas_to_dict(pkas_file:str, ) -> dict:
    """Origin: pkanalysis.py/read_experiment_pkas
    """
    fp = Path(pkas_file)
    if fp.name != "WT_pkas.csv":
        raise TypeError("Only wild type proteins listed in 'WT_pkas.csv' are currently considered.")

    translation = {"ARG": "ARG+",
                   "HIS": "HIS+",
                   "LYS": "LYS+",
                   "N-TERM": "NTR+",
                   "ASP": "ASP-",
                   "GLU": "GLU-",
                   "C-TERM": "CTR-",
                   "CYS": "CYS-",
                   "TYR": "TYR-"}

    pkas_df = pd.read_csv(fp,
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
               f'{translation[row["Res Name"]]}{row["Chain"]}{int(row["Res ID"]):04d}_')
        expl_pkas[key] = row["Expt. pKa"]

    return expl_pkas


def match_pkas(expr_pkas:dict, calc_pkas:dict) -> list:
    """Return a list of 3-tuples:
    (id=<pdb>/<res>, experimental pka, calculated pka).
    """

    #calculated_ids = []
    #for key in calc_pkas.keys():
    #    if key[0] not in calculated_ids:
    #        calculated_ids.append(key[0])

    calculated_ids = list(set([key[0].name for key in calc_pkas.keys()]))
    print(f"{calculated_ids = }") # temp

    pkas = []
    for key in expr_pkas.keys():
        if key[0] not in calculated_ids:
            continue

        if key in calc_pkas:
            calc_pka = calc_pkas[key]
        elif key[1][3] == "-":
            calc_pka = 0.0
        elif key[1][3] == "+":
            calc_pka = 14.0
        else:
            print(f"Parsing error of job pKas for {key}")

        pka = ("{}/{}".format(*key), expr_pkas[key], calc_pka)
        pkas.append(pka)

    return pkas


def matched_pkas_to_csv(matched_pkas:list, file_path:str="matched_pkas.csv") -> None:
    """Write a list of 3-tuples (as in a matched pkas list) to a comma separated file."""

    fp = Path(file_path)
    if fp.exists():
        raise FileExistsError(f"File {fp.name!r} already exists: either delete or rename it before saving.")

    if fp.suffix !=".csv":
        fp = fp.parent.joinpath(f"{fp.stem}.csv")

    with open(fp, "w") as fh:
        fh.writelines("{}, {}, {}\n".format(*pka) for pka in matched_pkas)

    return


def main():
    calc_pkas = read_calculated_pkas()
    expr_pkas = read_experiment_pkas()
    matched_pKas = match_pka(expr_pkas, calc_pkas)

    # Overall fitting
    x = np.array([p[1] for p in matched_pKas])
    y = np.array([p[2] for p in matched_pKas])
    delta = np.abs(x-y)
    m, b = np.polyfit(x, y, 1)
    rmsd = np.sqrt(np.mean((x-y)**2))
    within_2 = 0
    within_1 = 0
    n = len(matched_pKas)
    for d in delta:
        if d <= 2.0:
            within_2 += 1
            if d <= 1.0:
                within_1 += 1

    print("y=%.3fx + %.3f" %(m, b))
    print("RMSD between expr and calc = %.3f" % rmsd)
    print("%.1f%% within 2 pH unit" % (within_2/n*100))
    print("%.1f%% within 1 pH unit" % (within_1/n*100))

    save_pka(matched_pKas, fname="matched_pka.txt")

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
