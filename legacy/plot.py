#!/usr/bin/env python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

def read_pka(fname):
    lines = open(fname).readlines()
    names = []
    experiment = []
    calculated = []
    for line in lines:
        fields = line.split(",")
        names.append(fields[0])
        experiment.append(float(fields[1]))
        calculated.append(float(fields[2]))

    pkadb = {'name': names,
             'experiment': experiment,
             'calculated': calculated}

    return pkadb


def pka_stat(matched_pkas):
    x = np.array(matched_pkas['experiment'])
    y = np.array(matched_pkas['calculated'])
    delta = np.abs(x-y)

    m, b = np.polyfit(x, y, 1)
    rmsd = np.sqrt(np.mean((x-y)**2))
    within_2 = 0
    within_1 = 0
    within_15 = 0
    n = len(matched_pkas['experiment'])
    for d in delta:
        if d <= 2.0:
            within_2 += 1
            if d <= 1.5:
                within_15 += 1
                if d <= 1.0:
                    within_1 += 1

    print("y=%.3fx + %.3f" %(m, b))
    print("RMSD between expr and calc = %.3f" % rmsd)
    print("%.1f%% within 2 pH unit" % (within_2/n*100))
    print("%.1f%% within 1.5 pH unit" % (within_15 / n * 100))
    print("%.1f%% within 1 pH unit" % (within_1/n*100))


if __name__ == "__main__":

    pkadb1 = read_pka("matched_pka.txt")
    #pkadb2 = read_pka("matched_pka2.txt")

    print("At rotamer level 1:")
    pka_stat(pkadb1)

    #print("\nAt rotamer level 2:")
    #pka_stat(pkadb2)

    expr_pka  = pkadb1['experiment']
    calc_pka1 = pkadb1['calculated']
    #calc_pka2 = pkadb2['calculated']
    #pkadb = {'Experiment pKa': expr_pka,
    #         'Rotamer level 1': calc_pka1,
    #         'Rotamer level 2': calc_pka2}
    pkadb = {'Experiment pKa': expr_pka,
             'Rotamer level 1': calc_pka1}

    pka = pd.DataFrame(pkadb)
    df = pka.melt('Experiment pKa', var_name='Method', value_name='Calculated pKa')

    #fig = sns.scatterplot(x="Experiment pKa", y="Calculated pKa", hue='Method', alpha=.5, palette=['darkorange', 'dodgerblue'], s=30, data=df)
    fig = sns.scatterplot(x="Experiment pKa", y="Calculated pKa", hue='Method', alpha=.5, palette=['darkorange'], s=30, data=df)
    
    plt.plot([0, 14], [0, 14], '-', c='b', linewidth=2)
    plt.plot([0, 14], [1.5, 15.5], '--', c='g', linewidth=1, alpha=0.5)
    plt.plot([0, 14], [-1.5, 12.5], '--', c='g', linewidth=1, alpha=0.5)
    x = np.array([i for i in range(15)])
    fig.fill_between(x, x-1.5, x+1.5, alpha=0.05, color='g')
    fig.set(ylim=(-0.5, 14.5))

    #grid.ax_joint.plot([0, 4], [1.5, 0], 'b-', linewidth=2)

    #sns.lmplot(x="Experiment pKa", y="Calculated pKa", hue='Method', ci=10, data=df)

    # plt.plot(x, y, 'o')
    # plt.plot(x, x, '-', color="k")
    # plt.plot(x, x + 1, '--', color="y")
    # plt.plot(x, x - 1, '--', color="y")
    # plt.plot(x, x + 2, ':', color="r")
    # plt.plot(x, x - 2, ':', color="r")
    plt.show()
