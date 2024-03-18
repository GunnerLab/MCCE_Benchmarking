<!---..................................................................................................................|:120 --->
# Installing MCCE_Benchmarking & Testing:
  * Notation remarks:
    a. ">" denotes the command line prompt (whatever it may be in your profile);
    b. ">>" denotes the output of a command.
    c. On a command line, "<x>" is an example of an argument value.

## Start
  ### 0. Preferably: `>cd $HOME`

  ### 1. Install miniconda, if needed  
    1.2 (Optional) Configure .condarc for installation channels & packages included with all new env, e.g.:
    <details>
        <summary>[conda config]</summary>

        ```sh

        # user_rc_path
        channel_priority: strict
        channels:
          - conda-forge
          - bioconda
          - newbooks

        auto_update_conda: true
        report_errors: true

        # disallow install of specific packages
        disallow:
          - anaconda
        # Add pip, wheel, and setuptools as deps of Python
        add_pip_as_python_dependency: true

        create_default_packages:
          - numpy
          - ipython
          - ipykernel
          - python-dotenv
          - matplotlib
          - pandas
          - pytest
          - black
          - pylint
          - flake8
        ```
</details>

  ### 2. Create a dedicated environment for all things mcce:
    - e.g. 'mce'
     ```sh

     >conda create -n mce python=3.11   # the version part (=3.11) is optional, but not python

     ```
   - Activate the env:
     ```sh

     >conda activate mce  # => new prompt: (mce) >

     ```
   - Install mcce
     * For Gunner Lab members:
       [UPDATE, 03-01-2024:
       This is a MUST: the packaged 'Stable-MCCE' is missing a fortran library;
       See Issue 282, https://github.com/GunnerLab/Stable-MCCE/issues/282
       ]
       On the server, mcce is already installed, but it must be in your path variable; 
       Add the following line in your .bashrc, save & close the file, then source it:
       ```sh
       export PATH="/home/mcce/Stable-MCCE/bin:$PATH"
       ```
       ```sh

       (mce) > . ~/.bashrc   # source or 'dot' the file

       (mce) >which mcce     # should return the added path

       ```

     * For all others, install the package if Issue 282 is resolved:
       ```sh

       (mce) >conda install -c newbooks mcce

       ```

  ### 3. Install mcce_benchmark (right now from GitHub, not yet published on pypa):
  ```
  (mce) >pip install git+https://github.com/GunnerLab/MCCE_Benchmarking.git#egg=mcce_benchmark

  ```

  #### 3.1 Check that the installation created the 4 cli commands:
  (The commands will NOT be available outside your environment.)

  ```sh
  (mce) >which bench_setup
  >>~/miniconda3/envs/mce/bin/bench_setup

  (mce) >which bench_batch
  >>~/miniconda3/envs/mce/bin/bench_batch

  (mce) >which bench_analyze
  >>~/miniconda3/envs/mce/bin/bench_analyze

  (mce) >which bench_compare
  >>~/miniconda3/envs/mce/bin/bench_compare

  ```

  #### 3.2 Check the online help, e.g.:
  ```sh

  (mce) >bench_setup pkdb_pdbs --help

  (mce) >bench_setup user_pdbs --help

  ```
---

# Command line options
Here is a short survey of the available options.

## 1. To create a set using the pdbs from pKaDBv1, use the setup command & sub-command `bench_setup pkdb_pdbs`.
Note: `bench_setup` creates the run script with the command line options for the mcce steps; if none are given, the default run script is used.
  * Minimal input `-bench_dir`:
    ```sh
    
    (mce) >bench_setup pkdb_pdbs -bench_dir <some/dir>  # -bench_dir is a required arg
    
    ```
    
    You can limit the number of curated proteins (folder) to setup using `-n_pdbs`.
    Give a low number for testing (max is 120, default):
    ```sh
    
    (mce) >bench_setup pkdb_pdbs -bench_dir <some/dir> -n_pdbs <2>
    
    ```

  * `-job_name` option
   The default job name is 'default_run'; you can change it using `-job_name`.
    - If you use `-job_name` without amending any of the steps args, the default_run.sh file will be soft-linked as <job name>;
    - If you pass one or more non-default mcce steps parameters, then you MUST have a job name (& not 'default_run'):
    ```sh

    (mce) >bench_setup pkdb_pdbs -bench_dir <some/dir> -n_pdbs <2> -d 8 -job_name <foo_e8>
    
    ```

  * `-sentinel_file` option:
  The default sentinel_file is **pK.out** (means the run completed Step 4). It is part of script setup
  to ensure it is deleted prior to launching. You need to include it if you are not running all 4 steps. Example running only steps 1 & 2:
  ```sh

  (mce) >bench_setup pkdb_pdbs -bench_dir <some/dir> --s3_norun  --s4_norun -job_name <up_to_s2> -sentinel_file step2_out.pdb

  # OR
  (mce) >bench_setup user_pdbs -bench_dir <some/dir> -pdbs_list ./pdbs --s3_norun  --s4_norun -job_name <up_to_s2> -sentinel_file step2_out.pdb

  ```

### DO NOT USE `--launch` or `bench_setup launch`: the scheduling cannot run due to issues in `Stable-MCCE` packaging.
Instead, launch a batch of 10 runs every time this command is used:

```sh

(mce) >bench_batch -bench_dir <some/dir> -job_name <foo_e8> [-n_batch if not 10]   # 10 is the default batch size

```

  * `--launch` option (flag) means "create a crontab entry to scheduling the processing of all pdbs in the set".
  Launching the scheduled processing of the set with `bench_setup` is possible with the `--launch` flag:
  ```sh

  (mce) >bench_setup pkdb_pdbs -bench_dir <some/dir> -d 8 -job_name <foo_e8> --launch

  # OR
  (mce) >bench_setup user_pdbs -bench_dir <some/dir> -pdbs_list ./pdbs -d 8 -job_name <foo_e8> --launch

  ```

  In this case, you CANNOT review or amend the run script. You would not launch the job this way if, for instance,  
  you want to add Step 6.
  **TODO**: Step 6 will be part of the script once a hydrogen-bond network comparison procedure is finalized.

## 2. To create a set using a user-provided list of pdbs, use the setup command & sub-command `bench_setup user_pdbs`.

  * Minimal input `-bench_dir`, `-pdbs_list`:
  ```sh

  (mce) >bench_setup user_pdbs -bench_dir <some/dir>  -pdbs_list ./path/to/dir or ./path/to/file/of/pdbs filepaths

  ```

  * `-job_name` option: same usage as with `pkdb_pdbs` sub-command

  * `-sentinel_file` option: same usage as with `pkdb_pdbs` sub-command

  * `--launch` option (flag): same usage as with `pkdb_pdbs` sub-command

## 3. To launch batches of jobs, use `bench_setup launch`
   * Use the automated scheduling to process all the pdbs in batches of size n_batch (default 10):
   ```
   (mce) >bench_setup launch -bench_dir <some/dir> -job_name <foo> -n_batch <4> [-sentinel_file x]  # needed if used in setup

   ```

## 4. Analyze (one set):

The command line interface for analyzing a job setup via `bench_analyze [pkdb_pdbs or user_pdbs]`; requires 1 argument: `-bench_dir`.
The first step of the analysis checks that all the runs are completed. Incidentally, it's an easy way to check how far along the processing is.

  * Output files & sub-commands:
    - user_pdbs: Collated pK.out and sum_crg.out, res and confs count files & related figures
    - pkdb_pdbs: Analysis additionally includes res and confs stats viz experimental pKa values and related figures.


## 5. Compare two sets of runs, i.e. A/B testing (convention: B is reference):

To compare two (completed) sets of runs, use `bench_compare`:
  * Options: -di1, -dir2 -o (output folder), and two flags:
    * `--user_db_pdbs`      # absence means 'pkdb_pdbs'
    * `--dir2_is_refset`    # if used, --user_pdbs must NOT be present, e.g.:
    ```
    (mce) >bench_compare -dir1 <d1> dir2 parse.e4 --dir2_is_refset -o <d1/comp>

    ```


## 6. Give feedback in repo:
Please, open an issue with any problem installing or using the app, along with enhancement requests on the [MCCE_Benchmarking issues](https://github.com/GunnerLab/MCCE_Benchmarking/issues) page. Thanks.

<!---..................................................................................................................|:120 --->
