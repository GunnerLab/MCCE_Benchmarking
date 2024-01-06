"""Module: job_setup.py

Contains functions to prepare a user's benchmarking folder using user-provided options
(from cli args if cli is used).


* setup_pdbs_folder(user_job_folder):
 Create a copy of BENCH_PDBS in user_job_folder with only the relevant pdb (in case
 subfolders contain multiple pdb files), and "book.txt";
 Soft-link the relevant pdb as "prot.pdb";

* write_run_script(sub_command:str="start_from_step1", **args):
 Write a shell script in user_job_folder similar to RUN_SRC (default template):
 ```
 #!/bin/bash
 step1.py --dry prot.pdb
 step2.py -d 8
 step3.py -d 8
 step4.py
 sleep 10
 ```
 The script will be name as per args.job_name and its contents will differ depending on the chosen
 sub-command and associated options.
 NOTE: The other sub-command, "start_from_step3" is to be implemented after testing of the default one.

* launch_job(q_book, job_name, n_active:int = N_ACTIVE):
 cd user_job_folder/clean_pdbs
 call batch_submit.batch_run(q_book, job_name, n_active:int = N_ACTIVE)
  - q_book is the 'book.txt' file in user_job_folder.
  - batch_submit.batch_run was batch_submit.main()

* implement function for a fresh run in existing folder as per original instructions from jmao:
```
4. Start a fresh batch run
    * make prot.pdb ready
    * remove pK.out
    * make book file ready (clear the status code)
    * prepare job script - run.sh
    * edit 3 entries in bin/batch_submit.py
        n_active = 10   # keep this number of active jobs
        queue_book = "book.txt"
        job_name = "run.sh"
    * go to clean_pdbs directory, run ../bin/batch_submit.py
    * test if book.txt file has a new time stamp every time you run the batch_submit.py script.
```
"""

# import class of files resources and constants:
from benchmark import BENCH

RUN_SRC = """
#!/bin/bash
#step1.py --dry prot.pdb
#step2.py -d 8
#step3.py -d 8
#step4.py

sleep 10
"""
