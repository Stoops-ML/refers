import re
from pathlib import Path

import pytest


@pytest.fixture
def create_tmp_file(request, tmp_path):
    """
    Create temporary files.
    :param request: Tuple containing files to create
    :return: Path object of the first file given
    """
    for fname, flines in request.param:
        tmp_file = tmp_path / fname
        with open(tmp_file, "w") as f:
            f.write(flines)
    yield tmp_path / request.param[0][0]  # return path to first file given
    for fname, flines in request.param:
        fname = Path(fname)
        tmp_file = tmp_path / fname
        tmp_file.unlink()
        refers_file = tmp_path / (fname.stem + "_refers" + fname.suffix)
        if refers_file.is_file():
            refers_file.unlink()


@pytest.fixture
def create_files(request, tmp_path):
    """
    :param request: Tuple containing files to create
    :return:
    """

    tmp_folder = tmp_path / "test"
    tmp_folder.mkdir(exist_ok=True)
    for fname, flines in request.param:
        tmp_file = tmp_folder / fname
        with open(tmp_file, "w") as f:
            f.write(flines)
    yield tmp_folder


@pytest.fixture
def check_refers_test_files(request, tmp_path):
    """
    Check that *_refers files are only created for files that contain refs.
    All files in the refers_test_files folder must end (before the suffix): no_refs, with_refs, no_tags, or with_tags.
    :param request: Tuple containing files to create
    :return:
    """

    tmp_folder = tmp_path / "test"
    tmp_folder.mkdir(exist_ok=True)
    for fname, flines in request.param:
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
