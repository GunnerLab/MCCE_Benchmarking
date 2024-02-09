My understanding is you are close to completing program for comparison
 - Alexov pdb with Alexov experimental values [CC: NA: This IS the default dataset.]
 - Alexov pdb with standard Parse values      [CC: Reference parse.e4 dataset completed in isis]
 - [CC: TODO: Run pkanalysis on parse.e4 to output `matched_pka.csv`.]
    - [Issue15](https://github.com/GunnerLab/MCCE_Benchmarking/issues/15)

Complete and let us see how it works before going further.

Goal:    
- ‘Automatic’ program to compare MCCE pKas from multiple runs and/or experiment
- Comparison reference type:
  - experimental pKas – how good is the answers? [CC: jmao's pkanalysis.py]
  - pKs from a previous calculation – compare new calc with older mcce values.
    - [Issue16](https://github.com/GunnerLab/MCCE_Benchmarking/issues/16)

Input – ~~link~~ path to:  
 - PDB files: A  folder with pdb files that have been cleaned up.
   [CC: input is a directory path where to setup the curated pdbs. See README.]
- TPL directory  [CC: TODO:: create custom run script] - [Issue17](https://github.com/GunnerLab/MCCE_Benchmarking/issues/17)

- MCCE version   [CC: Determined by the user's conda environment.]

How to run (?) [CC: In README.md since 1/29/24.]  
Command line; input file with links to 3 input directories (pdb, tpl, mcce)?

Output:
 -  pK.out (including columns with mfe information)
    -  [CC: TODO: Add '--xts' on step4 as part of default script.]
    - [Issue9](https://github.com/GunnerLab/MCCE_Benchmarking/issues/9)
 -  [CC: TODO: Re-run `parse.e4` reference dataset to obtain mfe info in `pK.out`.]
    - [Issue10](https://github.com/GunnerLab/MCCE_Benchmarking/issues/10)
 -  count of number of conformers
    - [Issue13](https://github.com/GunnerLab/MCCE_Benchmarking/issues/13)
 -  time for calculation [CC: TODO: Function to parse the 'run' or 'progress' logs for time.]
    - [Issue12](https://github.com/GunnerLab/MCCE_Benchmarking/issues/12)

Analysis: Compare against referce file:  
For each residue type
 - Average ∆pK; RMDS; Count absolute value ∆pK <0.5;  ≥0.5, ≥1, ≥2,
 - [CC: TODO: Add 2 extra ranges to analysis:<0.5 & ≥0.5; Check aver. ∆pK is included.]
   - [Issue14](https://github.com/GunnerLab/MCCE_Benchmarking/issues/14)

