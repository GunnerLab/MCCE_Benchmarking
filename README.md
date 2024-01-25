# MCCE_Benchmarking
_beta version_

## Packaged `benchmark/data` folder contents
```
	data
	├── MT_pkas.csv
	├── WT_pkas.csv
	├── metadata.md
	├── proteins.tsv
	└── clean_pdbs/
```

## Experimental pKas data source
The original data comes from [Dr. Emil Axelov's pKa Database (1)](http://compbio.clemson.edu/lab/software/5/). The list for wild types and mutants alike was further curated by Dr. Junjun Mao at the Gunner Lab at CCNY to
mainly remove membrane proteins and those containing nucleotides, and to select the biological unit(s). The resulting files: `WT_pkas.csv` and `MT_pkas.csv`, contain the primary data needed for benchmarking purpose.
However, only the WT data is currently used as most of pKas of the mutant proteins were measured by NMR, hence
yield pKa _ranges_ rather than values.

#### pKa file header:
**'PDB ID', 'Res Name', 'Chain', 'Res ID', 'Expt. pKa', 'Expt. Uncertainty', '%SASA', 'Expt. method', 'Expt. salt conc','Expt. pH', 'Expt. temp', 'Reference'**

### File `proteins.tsv`:
Comments out the excluded pdbs and gives the reason. Column 'Model' identifies single- or multi- model structures.

### File `metadata.md`:
Experimental data source details; to be kept in data folder.

### Folder `clean_pdbs`:
Holds the prepared pdb files, which reside inside a folder with the same pdbid in upper case.
```
	data/clean_pdbs/
	├── book.txt		# Q_BOOK in the code
	├── default_run.sh
	├── 135L
	...
	├── 9RAT
	└── 9RNT
```

#### Multi-model structures:
The original file was renamed with an appended `.full` extension, in case we need to redo the spliting.  
The split files are kept (named 'modelnn.pdb'), but now the pdb to be used as 'prot.pdb' matches the 'proteins.tsv'
'Use' column -> pdbid_use.pdb is the new name, with 'use' being the string from the 'Use' column minus the period.

# TODO:
* Test bench cli with small number of processes.
