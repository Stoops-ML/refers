import pytest
import tempfile
from pathlib import Path
import re

TMP_DIR = Path(str(tempfile.tempdir))


@pytest.fixture
def create_tmp_file(request):
    """
    Create temporary files.
    :param request: Tuple containing files to create
    :return: Path object of the first file given
    """
    for (fname, flines) in request.param:
        tmp_file = TMP_DIR / fname
        with open(tmp_file, "w") as f:
            f.write(flines)
    yield TMP_DIR / request.param[0][0]  # return path to first file given
    for (fname, flines) in request.param:
        fname = Path(fname)
        tmp_file = TMP_DIR / fname
        tmp_file.unlink()
        refers_file = TMP_DIR / (fname.stem + "_refers" + fname.suffix)
        if refers_file.is_file():
            refers_file.unlink()


@pytest.fixture
def check_refers_test_files(request):
    """
    Check that *_refers files are only created for files that contain refs.
    All files in the refers_test_files folder must end (before the suffix): no_refs, with_refs, no_tags, or with_tags.
    :param request: Tuple containing files to create
    :return:
    """

    tmp_folder = TMP_DIR / "test"
    tmp_folder.mkdir(exist_ok=True)
    for (fname, flines) in request.param:
        tmp_file = tmp_folder / fname
        assert (
            re.search(
                rf"^.*(no_refs|with_refs|no_tags|with_tags){tmp_file.suffix}$",
                tmp_file.name,
            )
            is not None
        ), "All files in the refers_test_files folder must end (before the suffix): no_refs, with_refs, no_tags, or with_tags."
        with open(tmp_file, "w") as f:
            f.write(flines)
    yield tmp_folder
    refers_found = False
    for f in tmp_folder.rglob("*_refers.*"):  # type: ignore
        refers_found = True
        assert re.search(rf"^.*with_refs_refers{f.suffix}$", f.name) is not None  # type: ignore
    assert refers_found, "No document with _refers found"

    # clean up
    for f in tmp_folder.iterdir():  # type: ignore
        f.unlink()  # type: ignore
    tmp_folder.rmdir()
