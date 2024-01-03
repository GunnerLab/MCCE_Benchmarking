from argparse import ArgumentParser, RawDescriptionHelpFormatter
#import mcce_cdc.ms_analysis as msa
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import sys
import time
from typing import Union, TextIO


# TODO:
# 1. ID cli parameters
# 2. main fns:
#    setup_bench_dir
#    launch_batch

###############################################################

# Currently, the default output folders are used, i.e.g:
#   pdbs_dir = mcce_dir.joinpath(SAMPLED_PDBS)
#   parsed_dir = mcce_dir.joinpath(PARSED_PDBS)
#
SAMPLED_PDBS = "pdb_output_mc"
PARSED_PDBS = "parsed_pdb_output_mc"


def clear_folder(dir_path: str, file_type:str = None,
                 del_subdir:bool=False,
                subdir_startswith = "CDC_") -> None:
    """Delete all files in folder."""

    p = Path(dir_path)
    if not p.is_dir():
        # no folder, nothing to clear
        return

    if file_type is None:
        for f in p.iterdir():
            if not f.is_dir():
                f.unlink()
            else:
                if (del_subdir
                    and f.name.startswith(subdir_startswith)):
                    delete_folder(f)
    else:
        if file_type.startswith("."):
            fname = f"*{file_type}"
        else:
            fname = f"*.{file_type}"

        for f in p.glob(fname):
            f.unlink()
    return


def delete_folder(dir_path: str) -> None:
    """Delete folder and all files there in."""

    p = Path(dir_path)
    if not p.is_dir():
        return
    shutil.rmtree(str(p))

    return


def save_dict_to_txt(dict_data: dict, text_filepath: str) -> None:
    """
    Save a dict to a text file.
    Extracted from unused /structure.DynamicStructure and modified.
    """
    text_filepath = Path(text_filepath)
    if not text_filepath.suffixes:
        text_filepath = text_filepath + ".txt"

    with open(text_filepath, "w") as out:
        for k, v in dict_data.items():
            out.write(f"{k} : {v}\n")

    return


def confs_to_pdb(step2_fh: TextIO, selected_confs: list, output_pdb: str) -> None:
    """Read step2_out coordinate line for each conformer in list `selected_confs`
    and creates a pdb file.

    Args:
    step2_fh (TextIO): File handle of 'step2_out.pdb'.
    selected_confs (list): A microstate's list of conformer ids.
    output_pdb (str): Output pdb file_path.

    Note: step2_out.pdb format
    ATOM      1  CA  NTR A0001_001   2.696   5.785  12.711   2.000       0.001      01O000M000 "
    ATOM     44  HZ3 LYS A0001_002  -2.590   8.781   9.007   1.000       0.330      +1O000M000
    ATOM     45  N   VAL A0002_000   4.060   7.689  12.193   1.500      -0.350      BK____M000
    01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901
              1         2         3         4         5         6         7         8         9
    """

    with open(output_pdb, "w") as out:
        for line in step2_fh:
            if len(line) < 82:
                continue
            if line[80:82] == "BK":
                out.write(line)
                continue
            confID = line[17:20] + line[80:82] + line[21:26] + "_" + line[27:30]
            if confID in selected_confs:
                out.write(line)

    print(f"\tconfs_to_pdb - Written: {output_pdb}")
    return


def ms_sample_to_pdbs(sampled_ms: list,
                      conformers: list,
                      fixed_iconfs: list,
                      mcce_dir: str,
                      output_folder: str,
                      ) -> None:
    """Obtain a sample from the entire microstate space defined in msa.MSout.microstates,
    and for each ms in the sample gather its conformers and use them to create a pdb file.

    Args:
    sampled_ms (list): List of sampled [index, microstate object].
    conformers (list): List of conformers from head3.lst.
    fixed_iconfs (list): List of fixed conformers (from mso.fixed_iconfs).
    mcce_dir (str): MCCE output folder path.
    output_folder (str): Created pdb files output folder path.
    """

    step2_fh = open(mcce_dir.joinpath("step2_out.pdb"))

    for idx, sms in sampled_ms:
        pdb_out = output_folder.joinpath(f"ms_pdb_{idx}.pdb")
        if pdb_out.exists():
            print(f"\tms_sample_to_pdbs - pdb already exists: {pdb_out}.")
            continue

        pdb_confs = [conf.confid
                     for conf in conformers
                     if conf.iconf in sms.state
                     or conf.iconf in fixed_iconfs
                    ]
        # write the pdb file
        confs_to_pdb(step2_fh, pdb_confs, pdb_out)
        step2_fh.seek(0)

    step2_fh.close()
    print(f"\tms_sample_to_pdbs - over: {len(sampled_ms):,} Sampled microstates saved to pdbs in:\n\t{output_folder = }")

    return


def pdbs_to_gmx(mcce_dir:str, ms_mcce_pdb_dir: str, parsed_dir: str) -> None:
    """Convert MCCE formatted pdbs in `ms_mcce_pdb_dir` to gromacs format.

    Args:
    mcce_dir (str): path to mcce data folder; needed to access step2_out.pdb.
    ms_mcce_pdb_dir (str): Folder path for ms-mcce pdbs; should be 'mcce_dir/pdb_output_mc/'.
    parsed_dir (str): Folder path for the converted pdbs; should be 'mcce_dir/parsed_pdb_output_mc/'.
    """

    s2_path = mcce_dir.joinpath("step2_out.pdb")
    s2_rename_dict = mc2gmx.get_mcce_pdb_res_dict(s2_path)

    for fp in Path(ms_mcce_pdb_dir).glob("*.pdb"):
        pdb_out = f"{fp.stem}_gromacs.pdb"
        converter = mc2gmx.Mcce2GmxConverter(str(fp),
                                             s2_rename_dict,
                                             saving_dir=parsed_dir)
        converter.mcce_to_gromacs(pdb_out)
        print(f"\tConverted in {parsed_dir}: {pdb_out = }")

    return


def extract_residue_data(pdb_file: str) -> dict:
    """Used by ms_matrix."""
    residue_data = {}
    with open(pdb_file) as file:
        for line in file:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                # Only add residues where characters 94-97 are not '000'
                if characters_94_97 := line[93:97].strip() != "000":
                    residue_label = f"{line[16:20].strip()}_{line[20:26].strip()}"
                    if residue_label not in residue_data:
                        residue_data[residue_label] = characters_94_97

    return residue_data


def ms_matrix(parsed_pdb_folder: str, free_only:bool = False) -> None:
    """Save the sample microstate matrix as a csv file.
    Args:
    parsed_pdb_folder (str): Folder path for parsed (converted) pdbs
    free_only (bool, False): Flag to return data for free residues if True,
                             or all residues (default).
    """

    matrix = {}
    parsed_pdb_folder = Path(parsed_pdb_folder)
    for fp in parsed_pdb_folder.glob("*.pdb"):
        residue_data = extract_residue_data(fp)
        matrix[str(fp)] = residue_data

    # dict -> pd.df -> csv
    df = pd.DataFrame.from_dict(matrix, orient='index')

    csv_file = parsed_pdb_folder.joinpath("residue_matrix_free.csv")
    if csv_file.exists():
        print(f"\tms_matrix - {csv_file} already exists.")
    else:
        df.loc[:, (df != df.iloc[0]).any()].to_csv(csv_file)
        print(f"\tms_matrix - Created: {csv_file.name}")

    if not free_only:
        csv_file = parsed_pdb_folder.joinpath("residue_matrix.csv")
        if csv_file.exists():
            print(f"\tms_matrix - {csv_file} already exists.")
        else:
            df.to_csv(csv_file)
            print(f"\tms_matrix - Created: {csv_file.name}")

    return


def microstates_sites_energies(parsed_dir: str, cofactors_list: list = ["CLA","BCR","SQD","HOH"]):
    parsed_dir = Path(parsed_dir)

    # Dict to be saved as .npy:
    dict_site_energy = {}

    for fp in parsed_dir.glob("*.pdb"):
        pdb_name = fp.stem
        print("microstates_sites_energies -", fp)

        site_energy_list = []
        list_total_contribution = []

        scratch_dir = parsed_dir.joinpath(f"CDC_{pdb_name}")
        if scratch_dir.exists():
            clear_folder(scratch_dir)
        else:
            scratch_dir.mkdir()

        protein_atomic = ProteinAtomic(
            str(fp),
            "Isia",
            center_atomic = False,
            set_atomic_charges = True,
        )

        protein_atomic.prepare_pigments(
            "CLA",
            ChlorophyllAtomic,
            q_0011_charges_dict = "CLA_mcce",
            qy_atoms = ("N1B", "N1D"),
            qx_atoms = ("N1A", "N1C"),
        )

        # `calculate_cdc_site_shift` returns a tuple of dicts
        mcce_site_E_shift, mcce_total_contrib = calculate_cdc_site_shift(
            protein_atomic, dielectric_eff = 2.5, protein_contribution = True
        )
        #dict_site_energy_mcc = calculate_total_site_energy(mcce_site_E_shift, 14950, 15674)

        # Save the site energy dictionary for each microstate
        dict_site_energy[pdb_name] = mcce_site_E_shift

        # for debugging?
        #
        #cdc_results_dir = md_scratch_dir.joinpath("cdc_results")
        #if not cdc_results_dir.exists():
        #    cdc_results_dir.mkdir()
        #else:
        #    clear_folder(cdc_results_dir)

        #npy_contrib = cdc_results_dir.joinpath("dict_total_contribution_mcce.npy")
        #if npy_contrib.exists():
        #    print(f"\tmicrostates_sites_energies - {npy_contrib} already exists.")
        #else:
        #    np.save(npy_contrib, mcce_total_contrib)

        #fname = f"dict_site_energy_shift_most_occ_{cofactors_list}.txt"
        #path_shifts = cdc_results_dir.joinpath(fname)
        #if path_shifts.exists():
        #    print(f"\tmicrostates_sites_energies - {spath_shifts} already exists.")
        #else:
        #    save_dict_to_txt(mcce_site_E_shift, path_shifts)

        #fname = f"dict_total_site_energy_most_occ_{cofactors_list}.txt"
        #path_site_energy = cdc_results_dir.joinpath(fname)
        #if path_site_energy.exists():
        #    print(f"\tmicrostates_sites_energies - {path_site_energy} already exists.")
        #else:
        #    save_dict_to_txt(dict_site_energy_mcc, path_site_energy)


    dict_sites_npy = parsed_dir.joinpath("dict_site_energies.npy")
    if dict_sites_npy.exists():
        dict_sites_npy.unlink()
        #print(f"\tmicrostates_sites_energies - {dict_sites_npy} already exists.")
    else:
        np.save(dict_sites_npy, dict_site_energy, allow_pickle=True)

    delete_folder(scratch_dir)

    return


#.......................................................................
CLI_NAME = "mccecdc"  # as per pyproject.toml

# to be removed: only CLA is used:
cofactors_list = ["CLA","CLB","BCR","SQD","HOH","MEM"]

USAGE = f"{CLI_NAME} <sub-command for step to run> <args for step>\n"

DESC = """
    Run the 'MCCE_CDC pipeline' in 3 steps:
      step 1. ms sampling to pdbs
      step 2. mcce to gromacs pdbs conversion
      step 3. output files for sites energies (.npy) and ms matrices (.csv)

    The command for the pipeline is `mccecdc`, which expects a sub-command,
    one among `step1`, `step2` or `step3`, then the argument(s) for each.

    Output folders:
      pdbs_dir = mcce_dir/SAMPLED_PDBS
      parsed_dir = mcce_dir/PARSED_PDBS
      - These module variables hold the folder names:
          SAMPLED_PDBS = "pdb_output_mc"
          PARSED_PDBS = "parsed_pdb_output_mc"

"""

HELP_1 = f"""
    step 1: ms sampling to pdbs
    ------
    * Minimal number of arguments, 2: mcce dir and sample size
    * Commands: {CLI_NAME} step1 <step 1 args>
    * Example:
    {CLI_NAME} step1 /path/to/mcce 3

    * All other args have their default values:
     -msout_file: "pH7eH0ms.txt"
     -sampling_kind: deterministic
     -seed: None

"""
HELP_2 = f"""
    step 2: mcce to gromacs pdbs conversion
    ------
    * Minimal number of arguments, 1: mcce dir
    * Commands: {CLI_NAME} step2 <step 2 args>
    * Example:
    {CLI_NAME} step2 /path/to/mcce

"""
HELP_3 = f"""
    step 3: sites energies and create ms matrices
    ------
    * Minimal number of arguments, 1: mcce dir
    * Commands: {CLI_NAME} step3 <step 3 args>
    * Example:
    {CLI_NAME} step3 /path/to/mcce

    * All other args have their default values:
     - cofactors_list: ["CLA","CLB","BCR","SQD","HOH","MEM"]

"""


def do_ms_to_pdbs(args):
    "args: cli args for step1"

    if args.mcce_dir is None:
        raise ValueError("Invalid mcce_dir (None)")

    print("\tdo_ms_to_pdbs :: Retrieving args for step 1.\n")

    if args.sample_size <= 0:
        raise ValueError("Sample size must be > 0.")

    mcce_dir = Path(args.mcce_dir)
    msout_filepath = mcce_dir.joinpath("ms_out", args.msout_file)

    pdbs_dir = mcce_dir.joinpath(SAMPLED_PDBS)
    if not pdbs_dir.exists():
        pdbs_dir.mkdir()

    sampling_kind = "random"
    if args.sampling_kind[0].lower() == "d":
        sampling_kind = "deterministic"

    print("\tGettings conformers")
    conformers = msa.read_conformers(mcce_dir.joinpath("head3.lst"))

    print("\tInstantiating MSout")
    start = time.time()
    mso = msa.MSout(msout_filepath)
    d = time.time() - start
    print(f"\tInstantiating `msa.MSout` took {d/60:.2f} mins or {d:.2f} seconds")

    # informational
    ms_counts = msa.ms_counts(mso.microstates)
    print(f"\tNumber of unique microstates: {len(mso.microstates):,}",
          f"\tTotal number of microstates: {ms_counts = :,}", sep="\n")

    print("\tGettings fixed_iconfs")
    fixed_iconfs = mso.fixed_iconfs  # For ms_sample_to_pdbs.

    print("\tGettings sampled ms")
    sampled_ms = mso.get_sampled_ms(args.sample_size,
                                    kind = sampling_kind,
                                    seed = args.seed
                                   )

    print("\tCreating pdbs of sampled ms")
    ms_sample_to_pdbs(sampled_ms, conformers, fixed_iconfs, mcce_dir, pdbs_dir)

    return


def do_convert_pdbs(args):
    "args: cli args for step2"

    if args.mcce_dir is None:
        raise ValueError("Invalid mcce_dir (None)")

    print("\tdo_convert_pdbs :: Retrieving args for step 2.\n")

    mcce_dir = Path(args.mcce_dir)
    pdbs_dir = mcce_dir.joinpath(SAMPLED_PDBS)
    if not pdbs_dir.is_dir():
        raise FileNotFoundError(f"Missing {pdbs_dir}: forgot to run step1?")

    print("\tConverting mcce pdbs to gromacs")
    parsed_dir = mcce_dir.joinpath(PARSED_PDBS)

    if parsed_dir.exists():
        if args.empty_parsed_dir:
            clear_folder(parsed_dir, del_subdir=True)
            print(f"\tEmptied directory {parsed_dir}.")
    else:
        parsed_dir.mkdir()

    pdbs_to_gmx(mcce_dir, pdbs_dir, parsed_dir)

    return


def do_site_energies(args):
    "args: cli args for step3"

    if args.mcce_dir is None:
        raise ValueError("Invalid mcce_dir (None)")

    print("\tdo_site_energies :: Retrieving args for step 3.\n")

    mcce_dir = Path(args.mcce_dir)
    parsed_dir = mcce_dir.joinpath(PARSED_PDBS)
    if not parsed_dir.exists():
        raise FileNotFoundError(f"Missing {parsed_dir}: forgot to run step2?")

    print("\tGetting cofactors sites energies")
    microstates_sites_energies(parsed_dir, cofactors_list = args.cofactor_list)

    print("\tGetting matrices")
    ms_matrix(parsed_dir)

    return


def pipeline_parser():
    """Command line arguments parser with sub-commands defining steps in the
    mcce-CDC processing pipeline.
    """

    def arg_valid_dirpath(p: str):
        """Return resolved path from the command line."""
        if not len(p):
            return None
        return Path(p).resolve()

    p = ArgumentParser(
        prog = f"{CLI_NAME} ",
        description = DESC,
        usage = USAGE,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = ">>> END of %(prog)s.",
    )
    subparsers = p.add_subparsers(required=True,
                                  title='pipeline step commands',
                                  description='Subcommands of the MCCE-CDC processing pipeline',
                                  help='The 3 steps of the MCCE-CDC processing pipeline',
                                  dest='subparser_name'
                                 )

    # do_ms_to_pdbs
    step1 = subparsers.add_parser('step1',
                                  formatter_class = RawDescriptionHelpFormatter,
                                  help=HELP_1)
    step1.add_argument(
        "mcce_dir",
        type = arg_valid_dirpath,
        help = "The folder with files from a MCCE simulation; required.",
    )
    step1.add_argument(
        "sample_size",
        type = int,
        help = "The size of the microstates sample, hence the number of pdb files to write; required",
    )
    step1.add_argument(
        "-msout_file",
        type = str,
        default = "pH7eH0ms.txt",
        help = "Name of the mcce_dir/ms_out/ microstates file, `pHXeHYms.txt'; default: %(default)s.""",
    )
    step1.add_argument(
        "-sampling_kind",
        type = str,
        choices = ["d", "deterministic", "r", "random"],
        default = "r",
        help = """The sampling kind: 'deterministic': regularly spaced samples,
        'random': random indices over the microstates space; default: %(default)s.""",
    )
    step1.add_argument(
        "-seed",
        type = int,
        default = None,
        help = "The seed for random number generation. Only applies to random sampling; default: %(default)s.",
    )
    step1.set_defaults(func=do_ms_to_pdbs)

    # do_convert_pdbs
    step2 = subparsers.add_parser('step2',
                                  formatter_class = RawDescriptionHelpFormatter,
                                  help=HELP_2)
    step2.add_argument(
        "mcce_dir",
        type = arg_valid_dirpath,
        help = "The folder with files from a MCCE simulation; required.",
    )
    step2.add_argument(
        "-empty_parsed_dir",
        type = bool,
        default = True,
        # folder reuse:
        help = "If True, the pdb files in the folder `parsed_dir` will be deleted before the new conversion."
    )
    step2.set_defaults(func=do_convert_pdbs)

    # do_site_energies + matrices
    step3 = subparsers.add_parser('step3',
                                  formatter_class = RawDescriptionHelpFormatter,
                                  help=HELP_3)
    step3.add_argument(
        "mcce_dir",
        type = arg_valid_dirpath,
        help = "The folder with files from a MCCE simulation; required.",
    )
    # Remove? Current cofactor of interest is "CLA" (hard-coded in `microstates_sites_energies`).
    step3.add_argument(
        "-cofactor_list",
        type = list,
        default = cofactors_list,
        help="List of cofactors (3-char string) found in the pdb used in the MCC simulation; default: %(default)s.",
    )
    step3.set_defaults(func=do_site_energies)

    return p


def pipeline_cli(argv=None):
    """
    Command line interface to:
    - create a collection of pdb files from a mcce microstates sample.
    - convert the pdbs to gromacs format
    - create the sampled microstates matrix or matrices
    - calculate the site energy for CLA cofactor.
    """

    cli_parser = pipeline_parser()
    args = cli_parser.parse_args(argv)
    #if argv is None:
    #    cli_parser.print_help()
    #    return
    args.func(args)

    return


if __name__ == "__main__":
    pipeline_cli(sys.argv[1:])
