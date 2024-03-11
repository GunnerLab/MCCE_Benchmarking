# MCCE_Benchmarking
_beta version_

## Packaged `mcce_benchmark/data` folder contents
```
  ./
  ├── __init__.py
  ├── pkadbv1
  │   ├── WT_pkas.csv
  │   ├── metadata.md
  │   ├── proteins.tsv
  │   ├── RUNS/
  │   └── refsets/
  │       └── parse.e4/
  │           ├── analysis/
  │           └── RUNS/

```


## Experimental pKas data source
The original data comes from [Dr. Emil Axelov's pKa Database (1)](http://compbio.clemson.edu/lab/software/5/). The list for wild types and mutants alike was further curated by Dr. Junjun Mao at the Gunner Lab at CCNY to
mainly remove membrane proteins and those containing nucleotides, and to select the biological unit(s). The resulting file: `WT_pkas.csv` contains the primary data needed for benchmarking purpose.


#### pKa file header:
**'PDB ID', 'Res Name', 'Chain', 'Res ID', 'Expt. pKa', 'Expt. Uncertainty', '%SASA', 'Expt. method', 'Expt. salt conc','Expt. pH', 'Expt. temp', 'Reference'**

### File `proteins.tsv`:
Comments out the excluded pdbs and gives the reason. Column 'Model' identifies single- or multi- model structures.

### File `metadata.md`:
Experimental data source details; to be kept in data folder.

### Folder `RUNS`:
Holds the prepared pdb files, which reside inside a folder with the same pdbid in upper case.
```
	data/pkadbv1/RUNS/
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


## Command line interface (cli):
#### Description:
```
Description:
Launch a MCCE benchmarking job using curated structures from the pKa Database v1.

Entry points available at the command line:
 1. `bench_setup` along with one of 3 sub-commands:
  - Sub-command 1: 'pkdb_pdbs': setup data folders using the pdbs from pkadbv1 & the run script to run mcce steps 1 through 4;
  - Sub-command 2: 'user_pdbs': setup data folders using the pdbs provided via -pdbs_list option
  - Sub-command 3: 'launch': launch all the jobs via automated scheduling (crontab);
 2. `bench_launchjob` used to launch a batch of size n_batch
    Note: This is a convenience entry point that is used in the crontab (scheduler);
 3. `bench_analyze` along with one of 2 sub-commands:
  - Sub-command 1: 'pkdb_pdbs': analyze conformers and residues in user's 'benchmarks_dir'; get stats viz experiemntal pKas;
  - Sub-command 2: 'user_pdbs': analyze conformers and residues in user's 'benchmarks_dir';
 4. `bench_compare`: compare to sets of runs
```

#### Usage:
```
Examples for bench_setup: <+ 1 sub-command: pkdb_pdbs or user_pdbs or launch > <related args>\n

Examples:
1. pkdb_pdbs: Data & script setup using pkDBv1 pdbs:
   - Minimal input: value for -bench_dir option:
     >bench_setup pkdb_pdbs -bench_dir <folder path>

   - Using non-default option(s) (then job_name is required!):
     >bench_setup pkdb_pdbs -bench_dir <folder path> -d 8 -job_name <job_e8>

2. user_pdbs: Data & script setup using user's pdb list:
   - Minimal input: value for -bench_dir option, -pdb_list:
     >bench_setup user_pdbs -bench_dir <folder path> -pdb_list <path to dir with pdb files OR file listing pdbs paths>

   - Using non-default option(s) (then job_name is required! ):
     >bench_setup user_pdbs -bench_dir <folder path> -pdb_list <path> -d 8 -job_name <job_e8>

3. {launch}: Launch runs:
   - Minimal input: value for -bench_dir option: IFF no non-default job_name & sentinel_file were passed in {pkdb_pdbs}
     >bench_setup launch -bench_dir <folder path>

   - Using non-default option(s):
     >bench_setup launch -bench_dir <folder path> -n_batch <jobs to maintain>
    Note: if changing the default sentinel_file="pk.out" to, e.g. step2_out.pdb,
        then the 'norun' script parameters for step 3 & 4 must be set accordingly:
        >bench_setup launch -bench_dir <folder path> -sentinel_file step2_out.pdb --s3_norun --s4_norun
```


## Installation:

See [Install_and_Test](./Install_and_Test.txt) for ad-hoc installation until app is published.

