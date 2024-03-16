#!/usr/bin/env python

from collections import defaultdict
import logging
import matplotlib.pyplot as plt
from matplotlib import ticker, gridspec
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
import seaborn as sns


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

np.seterr(all='raise')


def plot_conf_thrup(tp_df:pd.DataFrame, n_complete:int, outfp:str=None) -> None:
    """
    Conformers throughput per mcce step.
    """

    tp_df = tp_df.rename(columns={"per_min_thrup":"y"})

    fig, ax = plt.subplots(1,1, figsize=(5,4))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel("# conformers/min")
    ax.set_xlabel("mcce step")
    ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda y, p: format(f"{int(y/1000)}K")))
    ax.get_xaxis().set_major_locator(MaxNLocator(integer=True))
    ax.set_title(f"Mean conformer throughput per minute\n(N={n_complete} pdbs)", y=.95)

    mx = tp_df.max()
    ofs = 1 # offset to start at 1
    istep = tp_df[tp_df.step == mx.step].index[0] + ofs

    markerline, stemlines, baseline = plt.stem(tp_df.index+ofs,
                                               tp_df.y,
                                               linefmt='grey',
                                               bottom=0)

    msize = 4
    plt.setp(markerline,
             ms=msize,
             markerfacecolor="tab:blue",
             markeredgecolor="tab:blue")

    plt.setp(stemlines, linewidth=.5, color="tab:blue")
    plt.setp(baseline, linewidth=.5, color="k")
    plt.plot(istep, mx.y, "o",
             label=f"{mx.y:,.0f}\nconfs/min",
             ms=msize+ofs,
             markerfacecolor="tab:red",
             markeredgecolor="tab:red")

    plt.grid(visible=True, which='major', axis='y', alpha=0.25)
    leg = ax.legend(title=f"Best: {mx.step.title()}",
               loc="upper center",
               bbox_to_anchor=(0.5, 0.9),
               borderaxespad = 0.,
               facecolor="tab:cyan",
               framealpha=0.1)
    if outfp is not None:
        plt.savefig(outfp)

    plt.show();


def plot_pkas_fit(matched_df:pd.DataFrame, pks_stats:dict, outfp:str=None) -> None:
    """Plot the best fit line of calculated vs experimental pKas
    for the matched pkas in the benchmark.
    Args:
    matched_df from pkanalysis.matched_pkas_to_df(matched_fp)
    pks_stats from pkanalysis.matched_pkas_stats(matched_fp)
    """

    # col1: calc - col2: ref or expl
    Y = matched_df.iloc[:,1]
    X = matched_df.iloc[:,2]

    sns.set_style("whitegrid")
    ax = sns.scatterplot(x=X, y=Y, alpha=0.4);
    ax.set_xlabel(f"{X.name} pKas; N matched = {pks_stats['N']:,}");
    ax.set_ylabel(f"{Y.name} pKas");
    sns.despine();

    cm = plt.get_cmap('tab20')
    a = 0.7
    if pks_stats["fit"] == "Failed LLS fit":
        logger.error("Data could not be fitted")
        return

    m, b = pks_stats["fit"]
    plt.plot(X, b + m * X,
             label=f"{m:.2f}.X + {b:.2f}",
             ls='-', lw=1,
             color="k", alpha=a);
    for c, v in enumerate(pks_stats["bounds"]):
        plt.plot(X, b + v + m * X, label=f"+/-{v}", ls = ':',
                 color=cm(c), alpha=a);
        plt.plot(X, b - v + m * X, ls = ':',
                 color=cm(c), alpha=a);
    nc = 1 + c
    plt.legend(bbox_to_anchor=(-0.05, 1.0, 1., .102),
               ncols=4,
               mode="expand",
               borderaxespad=0.)

    if outfp is not None:
        plt.savefig(outfp)

    plt.show();


def plot_res_analysis(matched_pKas:list, outfp:str=None) -> None:
    """
    Plot the best fit line of matched pKas grouped by residue.
    matched_pKas = pkanalysis.match_pkas(calc, ref)
    """

    matched_pKas = sorted(matched_pKas, key=lambda x: x[0][5:8])

    residues_stat = defaultdict(list)
    for pka in matched_pKas:
        resname = pka[0][5:8]
        residues_stat[resname].append((pka[1], pka[2]))

    residues_stat = dict(residues_stat)
    N_ioniz = len(residues_stat.keys())
    n_cells = int(N_ioniz**(1/2)) + 1

    cm = plt.get_cmap('tab20')
    fig = plt.figure(figsize=(10,10))
    gs = gridspec.GridSpec(n_cells, n_cells)

    for i, k in enumerate(residues_stat):
        ax = fig.add_subplot(gs[i])
        y = np.array([p[0] for p in residues_stat[k]])
        x = np.array([p[1] for p in residues_stat[k]])
        ax.plot(x, y, "o", color=cm(i+1))

        converged = True
        err_msg = None
        try:
            m, b = np.polyfit(x, y, 1)
        except Exception as e:
            #(np.linalg.LinAlgError, RuntimeWarning, FloatingPointError, RankWarning) as e:
            #RankWarning: Polyfit may be poorly conditioned
            #RuntimeWarning: invalid value encountered in divide
            #("SVD did not converge in Linear Least Squares")
            converged = False
            err_msg = str(e)
            m, b = 0,0

        if converged:
            ax.plot(x, m * x + b, ':', color="k")
            ax.set_title(k, y=1.0, pad=-12)
        else:
            ax.set_title(k + f": {err_msg}", y=1.0, pad=-12)

    if outfp is not None:
        plt.savefig(outfp)

    plt.show();
