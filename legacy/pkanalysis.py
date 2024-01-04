#!/usr/bin/env python
import pandas
import matplotlib.pyplot as plt
import numpy as np

def read_calculated_pkas():
    lines = open("book").readlines()
    workingdirs = []
    for line in lines:
        fields = line.split()
        if len(fields) == 2:
            if fields[1].lower() == "c":
                workingdirs.append(fields[0])

    calc_pkas = {}
    for dir in workingdirs:
        lines = open(dir+"/pK.out").readlines()
        lines.pop(0)
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


def read_experiment_pkas():
    df = pandas.read_csv("../WT_pka.csv", comment="#")

    pkas = df[["PDB ID", "Res Name", "Chain", "Res ID", "Expt. pKa"]]
    experiment_pkas = {}

    translation = {"ARG": "ARG+",
                   "HIS": "HIS+",
                   "LYS": "LYS+",
                   "N-TERM": "NTR+",
                   "ASP": "ASP-",
                   "GLU": "GLU-",
                   "C-TERM": "CTR-",
                   "CYS": "CYS-",
                   "TYR": "TYR-"}

    for _, row in pkas.iterrows():
        pdb = row["PDB ID"]
        resname = row["Res Name"]
        chain = row["Chain"]
        resseq = int(row["Res ID"])
        try:
            pka = float(row["Expt. pKa"].strip())
        except:
            #print(pdb, resname, chain, resseq, row["Expt. pKa"])
            continue

        key = (pdb, translation[resname.upper()] + chain + "%04d"%resseq + "_")
        experiment_pkas[key] = pka

        #    print(pdb, resname, chain, resseq, pka)

    return experiment_pkas

def match_pka(expr_pkas, calc_pkas):
    "Return a list of (ID experiment_pKa calculated_pka)."
    calculated_ids = []
    for key in calc_pkas.keys():
        if key[0] not in calculated_ids:
            calculated_ids.append(key[0])

    pkas = []
    for key in expr_pkas.keys():
        if key[0] not in calculated_ids:
            continue

        id = "%s/%s" % key
        if key in calc_pkas:
            calc_pka = calc_pkas[key]
        elif key[1][3] == "-":
            calc_pka = 0.0
        elif key[1][3] == "+":
            calc_pka = 14.0
        else:
            print("error at resname %s" % str(key))

        pka = (id, expr_pkas[key], calc_pka)
        pkas.append(pka)

    return pkas


def save_pka(pkadb, fname="matched_pka.txt"):
    lines = []
    for pka in pkadb:
        lines.append("%s, %s, %s\n" % pka)
    open(fname, "w").writelines(lines)


if __name__ == "__main__":
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