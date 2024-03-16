import pytest
from pathlib import Path
from mcce_benchmark.scheduling import extract_conda_init
from mcce_benchmark.scheduling import subprocess_run
import subprocess
import shutil


class TestExtractCondaInit:

    # The function should create a file named ~/.bashrc_conda if it does not exist.
    def test_create_bashrc_conda(self):
        # Remove ~/.bashrc_conda if it exists
        bc = Path("~/.bashrc_conda").expanduser()
        if bc.exists():
            bc.unlink()

        extract_conda_init()

        assert bc.exists() == True

    def test_error_if_bashrc_no_snippet(self):

        # Remove ~/.bashrc_conda if it exists
        bc = Path("~/.bashrc_conda").expanduser()
        if bc.exists():
            bc.unlink()

        brc = Path("~/.bashrc").expanduser()
        brc_copy = Path("~/.bashrc.bkp").expanduser()
        shutil.copyfile(brc, brc_copy)

        # Remove conda initialization snippet from brc_copy if it exists
        cmd = f"sed -i '/# >>> conda initialize/,/# <<< conda initialize/d' {brc_copy}"
        out = subprocess_run(cmd)
        print(type(out))

        with pytest.raises(subprocess.CalledProcessError):
            extract_conda_init(brc_file=brc_copy)

        # remove copy
        brc_copy.unlink()
