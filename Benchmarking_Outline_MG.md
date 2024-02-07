My understanding is you are close to completing program for comparison  
 - 	Alexov pdb with Alexov experimental values
 -	Alexov pdb with standard Parse values
Complete and let us see how it works before going further.  

Goal  
-‘Automatic’ program to compare MCCE pKas from multiple runs and/or experiment  
Comparison reference type:  
 - 	experimental pKas – how good is the answers?
 - 	pKs from a previous calculation – compare new calc with older mcce values.

Input – link to  
PDB files: A  folder with pdb files that have been cleaned up.  
TPL directory  
MCCE version  

How to run (?)  
Command line; input file with links to 3 input directories (pdb, tpl, mcce)?  

Output:   
 -	pK.out (including columns with mfe information)
 -	count of number of conformers
 -	time for calculation

Analysis: Compare against referce file  
For each residue type  
 -	Average ∆pK; RMDS; Count absolute value ∆pK <0.5;  ≥0.5, ≥1, ≥2,

