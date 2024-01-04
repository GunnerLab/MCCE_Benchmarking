#!/usr/bin/env python

INPUT = "WT_pkas.csv"

import pandas

df = pandas.read_csv(INPUT, comment="#")

pkas = df[["PDB ID", "Res Name", "Chain", "Res ID", "Expt. pKa"]]

pdbs = []

for _, row in pkas.iterrows():
    pdb = row["PDB ID"]
    resname = row["Res Name"]
    if resname == "C-term":
        resname = "CTR"
    elif resname == "N-term":
        resname = "NTR"

    chain = row["Chain"]
    resseq = int(row["Res ID"])
    try:
        pka = float(row["Expt. pKa"])
    except:
        continue

    pdbs.append(pdb)

pdbs=list(set(pdbs))
pdbs.sort()
for x in pdbs:
    print(x)
