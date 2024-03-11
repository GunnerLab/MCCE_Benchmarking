#!/usr/bin/env python

"""
Module: diff_mc

Subtract two Monte Carlo sampling result reports.
The reports can be fort.38, sum_crg.out, or anything with matching columns.
"""

from pathlib import Path


class MCfile:
    def __init__(self):
        self.type = ""
        self.pHs = []
        self.names = []
        self.values = {}

    def readfile(self, fname):
        lines = open(fname).readlines()
        line = lines.pop(0)
        fields = line.strip().split()
        self.type = fields[0]
        if self.type.upper() == "PH":
            self.pHs = ["%6.1f" % float(x) for x in fields[1:]]
        else:
            self.pHs = ["%6.f" % float(x) for x in fields[1:]]
        for line in lines:
            fields = line.strip().split()
            if len(fields) > 1:
                name = fields[0]
                self.names.append(name)
                for i in range(len(fields)-1):
                    self.values[(name, self.pHs[i])] = fields[i+1]

    def to_tsv(self, tsv_fp):
        with open(tsv_fp, "w") as fo:
            fo.writeline("%-14s %s\n" % (self.type, "\t".join(self.pHs)))
            for name in self.names:
                fo.writeline("%-14s %s\n" % (name, "\t".join(["%6s" % self.values[(name, ph)] for ph in self.pHs])))


    def printme(self):
        print("%-14s %s" % (self.type, " ".join(self.pHs)))
        for name in self.names:
            print("%-14s %s" % (name, " ".join(["%6s" % self.values[(name, ph)] for ph in self.pHs])))


def merge_lists(list1, list2):
    "Return a merged list while preserving order."

    ipos = 0
    list_merged = []
    for x in list1:
        if x not in list_merged:
            if x in list2:
                xpos = list2.index(x)
                list_merged += list2[ipos:xpos]
                ipos = xpos + 1
            list_merged.append(x)

    # list2 might have extra items
    if len(list2) > ipos:
        list_merged += list2[ipos:]

    return list_merged


def diff(f1, f2):
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
                values[key] = "%6.2f" % (float(f1.values[key]) - float(f2.values[key]))

    delta = MCfile()
    delta.type = f1.type
    delta.pHs = pHs
    delta.names = names
    delta.values = values

    return delta


def get_diff(fp1, fp2, save_to_tsv:str=None):

    f1 = MCfile()
    f1.readfile(fp1)

    f2 = MCfile()
    f2.readfile(fp2)

    delta = diff(f1, f2)
    if save_to_tsv is not None:
        delta.to_tsv(save_to_tsv)
        return
    else:
	delta.printme()

    return
