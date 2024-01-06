from importlib import resources


MCCE_OUTPUTS = ["acc.atm", "acc.res", "entropy.out", "fort.38",
                "head1.lst", "head2.lst", "head3.lst",
                "mc_out", "name.txt", "new.tpl",
                "pK.out", "respair.lst", "rot_stat",
                "run.log", "run.prm", "run.prm.record",
                "step0_out.pdb", "step1_out.pdb",
                "step2_out.pdb", "step3_out.pdb",
                "sum_crg.out", "vdw0.lst",
               ]


class Bench_Resources():
    """Immutable class to store package data paths and main constants."""

    __slots__ = ("_BENCH_DATA",
            "_BENCH_WT",
            "_BENCH_PROTS",
            "_BENCH_PDBS",
            "_Q_BOOK",
            "_BENCH_Q_BOOK",
            "_N_ACTIVE")

    def __init__(self, res_files=resources.files("benchmark.data")):

        self._BENCH_DATA = res_files
        self._BENCH_WT = self._BENCH_DATA.joinpath("WT_pkas.csv")
        self._BENCH_PROTS = self._BENCH_DATA.joinpath("proteins.tsv")
        self._BENCH_PDBS = self._BENCH_DATA.joinpath("clean_pdbs")
        self._Q_BOOK = "book.txt"
        self._BENCH_Q_BOOK = self._BENCH_DATA.joinpath(self._Q_BOOK)
        self._N_ACTIVE = 10   # number of active jobs to maintain

    @property
    def BENCH_DATA(self):
        return self._BENCH_DATA

    @property
    def BENCH_WT(self):
        return self._BENCH_WT

    @property
    def BENCH_PROTS(self):
        return self._BENCH_PROTS

    @property
    def BENCH_PDBS(self):
        return self._BENCH_PDBS

    @property
    def Q_BOOK(self):
        return self._Q_BOOK

    @property
    def BENCH_Q_BOOK(self):
        return self._BENCH_Q_BOOK

    @property
    def N_ACTIVE(self):
        return self._N_ACTIVE

    def __str__(self):
        out = f"""
        BENCH_DATA = {str(self.BENCH_DATA)}
        BENCH_WT = {str(self.BENCH_WT)}
        BENCH_PROTS = {str(self.BENCH_PROTS)}
        BENCH_PDBS = {str(self.BENCH_PDBS)}
        BENCH_Q_BOOK = {str(self.BENCH_Q_BOOK)}
        Q_BOOK = {str(self.Q_BOOK)}
        N_ACTIVE = {str(self.N_ACTIVE)}
        """

        return out


BENCH = Bench_Resources()
