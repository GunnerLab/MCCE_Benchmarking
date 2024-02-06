<!-- dotted line width = 120
........................................................................................................................-->
# Benchmarking Project

## Legacy

### Experimental pKas data source
The original data comes from [Dr. Emil Axelov's pKa Database (v1)](http://compbio.clemson.edu/lab/software/5/).  
The pKaDB data was split by wild-type or mutant and saved into files `WT_pkas.csv` and `MT_pkas.csv`.  
These files are used for the analysis as they provide the reference pka per all ionizable residues in protein X,
chain Y.  

However, only the WT data is currently used as most of pKas of the mutant proteins were measured by NMR, hence  
yield pKa _ranges_ rather than values.

The list for wild types and mutants alike was further curated by Dr. Junjun Mao at the Gunner Lab at CCNY to mainly:
 - remove membrane proteins and those containing nucleotides
 - select the biological unit(s).

The result of this curation consists of the file `proteins.tsv`: commented lines denote proteins not fit for the  
current mcce impementation, along with the specific reason; while the others provide infomation as per the file  
header ([PDB, Biounit, Use, Model], e.g.:`4HHB    4       A-D     single`). 


### Benchmarking code by Dr. Junjun Mao

The legacy implementation consisted of:  
 - A folder holding the above-described files and a "resusable subfolder" called `clean_pdbs` for the curated proteins.
 - A code base consisting of several python modules and a bash script to run all first 4 mcce steps.
 - No installation other than copying and pasting data and code [as far as I understand].
 - Navigation to the 'correct' subfolder is necessary to run the `pkanalysis.py` module.
 - The main product of this analysis is the "matched pKas file" (`matched_pka.csv`), which returns 3 columns: _id=pdb/res_,  
_experimental pka_, _calculated pka_.
 - The 'experimental pka' column in the "matched pKas file" comes from the pKaDB.
 - The `plot.py` module computes and plots the best fit line of calculated vs experiemntal pKas.
 - The scheduling of the mcce runs over the entire dataset is possible by manually creating a crontab for the run script.


### Refactored codebase by Dr. Cat Chenal
The current (beta) version of the benchmarking code base resides in this repo: [GunnerLab/MCCE_Benchmarking](https://github.com/GunnerLab/MCCE_Benchmarking).

#### Planned publishing:
As with the "Stable_MCCE" code base, the "MCCE_Benchmarking" package will be available for the world at large and will  
be installable via pip or conda (currently pip only). 

#### Curated data is packaged:
The package includes the curated data (single point of truth), which is installed in the user's specified folder via the cli  
subcommand for the (initial) data setup phase; the pdb to use is soft-linked as `prot.pdb`, not copied.  
Before inclusion, the verification of the data integrity was done using various functions from the `audit.py` module.  
New conventions were established in order to maintain this data integrity, especially that of the multi-model structures.  

##### Multi-model structures:
The original file was renamed with an appended `.full` extension, in case we need to redo the spliting.  
The split files are kept (named 'modelnn.pdb'), but now the name of the pdb to be used as 'prot.pdb' matches the 'Use' column  
in `proteins.tsv`, that is 'pdbid_use.pdb' is the new name, with 'use' being the string from the 'Use' column minus the period.


### Features - status:
 - Automated scheduling - testing, near completion
 - Inclusion of `pkanalysis.py` into the cli - TODO
 - Implement an analysis switch function depending on the reference set, i.e. "pKa DB" or one of the "reference mcce run(s)" - TODO
 - Include the pKas from the "reference mcce run(s)", i.e. "parse.e4", "parse.e8" into the packaged data - TODO
 - Implement formal testing - partial


### Discussion:
 - What should a "pKa analysis" include in addition to `matched_pka.csv`?
