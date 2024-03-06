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
  │   └── clean_pdbs/
  └── refsets
      └── parse.e4/
          ├── analysis/
          ├── clean_pdbs/
          └── all_pkas.out
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

### Folder `clean_pdbs`:
Holds the prepared pdb files, which reside inside a folder with the same pdbid in upper case.
```
	data/pkadbv1/clean_pdbs/
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
 1. 'bench_expl_pkas' along with one of 2 sub-commands:
  - Sub-command 1: 'setup_job': setup data folders & the run script to run mcce steps 1 through 4;
  - Sub-command 2: 'launch_job': launch a batch of jobs;
 2. 'bench_launchjob' used to lauch a batch of job as per n_batch
    Note: This is a convenience entry point that is used in the crontab (scheduler);
          It is the same as 'bench_expl_pkas launch_job -benchmarks_dir <dir> [+ args, e.g. n_batch 5]';
          It can be used via cli if scheduler fails.
 3. 'bench_analyze' along with one of 1 sub-command:
  - Sub-command 1: 'expl_pkas': analyze conformers and residues in user's 'benchmarks_dir';
```

#### Usage:
```
bench_expl_pkas setup_job <related args>

Examples for current implementation (Beta):

1. Job setup
 - Using defaults (benchmarks_dir= mcce_benchmarks):
   >bench_expl_pkas setup_job

 - Using non-default option(s):
   >bench_expl_pkas setup_job -benchmarks_dir <different name>
   >bench_expl_pkas setup_job -job_name <my_job_name>
   >bench_expl_pkas setup_job -job_name <my_job_name> -d 8

2. Submit batch of jobs (if done via the cli):
 - Using defaults (benchmarks_dir= mcce_benchmarks;
                   job_name= default_run;
                   n_batch= 10;
                   sentinel_file= pK.out):
   >bench_expl_pkas launch_job
```


## Installation:

See [Install_and_Test](./Install_and_Test.txt) for ad-hoc installation until app is published.

