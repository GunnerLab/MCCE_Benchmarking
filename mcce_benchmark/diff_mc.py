#!/usr/bin/env python

"""
Module: diff_mc

Subtract two Monte Carlo sampling result reports.
The reports can be fort.38, sum_crg.out, or anything with matching columns.
"""

from pathlib import Path
from typing import Union

class MCfile:
    def __init__(self, fname:Union[str, None]=None):
        self.fname = fname
        self.type = ""
        self.pHs = []
        self.names = []
        self.values = {}

    def readfile(self):
        if self.fname is None:
            print("Class instanciated without fname.")
            return

        lines = open(self.fname).readlines()
        hdr = lines.pop(0)
        fields = hdr.strip().split()
        self.type = fields[0]
        prec = 0
        if self.type.upper() == "PH": prec = 1
        self.pHs = [f"{float(x.strip()):.{prec}f}" for x in fields[1:]]

        for line in lines:
            fields = line.strip().split()
            if len(fields) > 1:
                name = fields[0]
                self.names.append(name)
                for i in range(len(fields)-1):
                    self.values[(name, self.pHs[i])] = fields[i+1]

    def to_tsv(self, tsv_fp):
        with open(tsv_fp, "w") as fo:
            fo.writelines("%s\t%s\n" % (self.type, "\t".join(self.pHs)))
            for name in self.names:
                fo.writelines("%s\t%s\n" % (name, "\t".join(["%s" % self.values[(name, ph)] for ph in self.pHs])))


    def __str__(self):
        out = "%-14s %s" % (self.type, " ".join(self.pHs))
        for name in self.names:
            out = out + "%-14s %s" % (name, " ".join(["%6s" % self.values[(name, ph)] for ph in self.pHs]))


def merge_lists(list1:list, list2:list) -> list:
    "Return a merged list while preserving order."

    ipos = 0
    list_merged = []
    for x in list2:  #ref
        if x not in list_merged:
            if x in list1:
                xpos = list1.index(x)
                list_merged += list1[ipos:xpos]
                ipos = xpos + 1
            list_merged.append(x)

    # list1 might have extra items
    if len(list1) > ipos:
        list_merged += list1[ipos:]

    return list_merged


def diff(f1:MCfile, f2:MCfile) -> MCfile:
    if f1.type != f2.type:
        return None

    # get merged pH
    pHs = merge_lists(f1.pHs, f2.pHs)

    # get merged names
    names = merge_lists(f1.names, f2.names)

    values = {}
    for name in names:
        for ph in pHs:
            key = (name, ph)
            if key in f1.values and key not in f2.values:
                values[key] = "<<<"
            elif key not in f1.values and key in f2.values:
                values[key] = ">>>"
            else:  # must be in both
                # f2 - f1 to get A - B??
                values[key] = "%6.2f" % (float(f2.values[key]) - float(f1.values[key]))

    delta = MCfile()
    delta.type = f1.type
    delta.pHs = pHs
    delta.names = names
    delta.values = values

    return delta


def get_diff(fp1:str, fp2:str, save_to_tsv:str=None) -> None:

    mcf1 = MCfile(fp1)
    mcf1.readfile()

    mcf2 = MCfile(fp2)
    mcf2.readfile()

    delta = diff(mcf1, mcf2)
    if save_to_tsv is not None:
        delta.to_tsv(save_to_tsv)
        return
    print(delta)

    return
