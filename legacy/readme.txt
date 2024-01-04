How to automate job submit
1. The source of experiment pKas
    Emil's pKa database v1: WT_pka.csv and MT_pka.csv.
    The structures were inspected manually and the comments are in file proteins.

2. Folder and file structure
    * scripts location: bin
      The submit scripts, analysis tools are in this directory. The mcce job script is placed in working directory.
    * working directory: clean_pdb holds all calculatable structures.
    * bookkeeping file: book. This file tracks automation. The letter after the pdb id means
        r: running state
        e: error state
        c: completed state which means pK.out is present
    * protein description: proteins

3. Submit script - batch_submit.py
    Every time when this script is called, it
    * reads bookkeeping file to know the running jobs
    * runs "ps" to know how many the named jobs are running and their directories
    * compares the bookkeeping file and current running jobs to decide job status (r, e, or c)
    * if the running jobs are less than threshold, submit new jobs

    Implications:
    * if a job has an error, you can go to the working directory and correct it, then remove the code e
    * if you are working on two batches of calculations, the job script needs to have a different name

4. Start a fresh batch run
    * make prot.pdb ready
    * remove pK.out
    * make book file ready (clear the status code)
    * prepare job script - run.sh
    * edit 3 entries in bin/batch_submit.py
        n_active = 10   # keep this number of active jobs
        queue_book = "book"
        job_name = "run.sh"
    * go to batch directory, run ../bin/batch_submit.py
    * test if book file has a new time stamp every time you run the batch_submit.py script.

5. Set up cron job to automate
    The job status and new job submission only happen when the script batch_submit.py is called.
    One easy way to automate the job is to run batch_submit.py from crontab.
    crontab -e

    Here is my example:
    PATH=/home/jmao/miniconda3/bin:/home/jmao/Stable-MCCE/bin:/home/jmao/bin:/home/jmao/miniconda3/condabin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
    *  *   *   *   *     cd /home/jmao/benchmark/e08_calc && /home/jmao/benchmark/bin/batch_submit.py >/tmp/cron.log 2>&1

    The first line tells cron the PATH, as PATH in shell is different from crom. Using echo $PATH to see the path works for you in shell.
    The second line is to run the script in batch directory every minute. If you would like to run every 5 minutes:
    */5 * * * *

6. Monitor job
    Check book file and examine the code of each pdb directory.
    r: running
    e: error
    c: finished

    To rerun job, just delete the status code, and pK.out if any.

7. Result analysis
    * pkanalysis.py will create file matched_pka.txt, plot.py will plot the pkas from matched_pka.txt
    * analysis.ipynb does the same under Jupyter Notebook
