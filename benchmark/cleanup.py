"""
Module: cleanup.py

Contains functions to clear a folder, delete a folder, etc.
"""

from benchmark import MCCE_OUTPUTS
from pathlib import Path
import shutil


def delete_mcce_outputs(mcce_dir:str) -> None:
    """Delete all MCCE output files or folders from a MCCE run folder.
    Note: All subfolders within `mcce_dir` are automatically deleted.
    """

    folder = Path(mcce_dir)
    if not folder.is_dir():
        print(f"{folder = } does not exist.")
        return

    for fp in folder.iterdir():
        if fp.is_dir():
            shutil.rmtree(fp)
        else:
            if fp.name in MCCE_OUTPUTS:
                fp.unlink()

    return


def clean_job_folder(job_dir:str) -> None:
    """Delete all MCCE output files and folders from a directory `job_dir`,
    which is a folder of folder named after the pdb id they contain.
    """
    pdbs_dir = Path(job_dir)
    for fp in pdbs_dir.iterdir():
        if fp.is_dir():
            delete_mcce_outputs(fp)
        else:
            print(f"{fp = }: remaining")

    return


def clear_folder(dir_path: str, file_type:str = None,
                 del_subdir:bool = False,
                 del_subdir_begin:str = None) -> None:
    """Delete all files in folder.
    Only delete subfolders if `del_subdir` is True and the subdir
    name starts with `del_subdir_begin` if non-zero length str.
    Note: `del_subdir_begin` must neither be None or "" if `del_subdir`
    is True.
    """

    # validate del_subdir_begin:
    if del_subdir:
        if del_subdir_begin is None or len(del_subdir_begin) == 0:
            del_subdir = False

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
                    and f.name.startswith(del_subdir_begin)):
                    shutil.rmtree(str(f))
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
