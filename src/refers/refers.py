import warnings
from refers.errors import (
    TagAlreadyExistsError,
    MultipleTagsInOneLine,
    TagNotFoundError,
    PyprojectNotFound,
)
from typing import Dict
from typing import Optional
from typing import List
from typing import Tuple
from typing import Union
import re
from pathlib import Path
from refers.definitions import (
    CODE_RE_TAG,
    UNKNOWN_ID,
    DOC_REGEX_TAG,
    DOC_OUT_ID,
    LIBRARY_NAME,
    COMMENT_SYMBOL,
)
import toml


def get_files(
    pdir: Path,
    accepted_extensions: Optional[List[str]] = None,
    dirs2ignore: Optional[List[Path]] = None,
    dirs2search: Optional[List[Path]] = None,
):
    if dirs2ignore is None:
        dirs2ignore = []
    for f in pdir.rglob(r"*.*"):  # only files
        if (
            f.parent in dirs2ignore
            or (dirs2search is not None and f.parent not in dirs2search)
            or (
                accepted_extensions is not None
                and f.suffix.lower() not in accepted_extensions
            )
        ):
            continue
        yield f


def get_tags(
    pdir: Path,
    accepted_tag_extensions: Optional[List[str]] = None,
    dirs2search: Optional[List[Path]] = None,
    dirs2ignore: Optional[List[Path]] = None,
    tag_files: Optional[List[Path]] = None,
) -> Dict[str, Tuple[Path, int, str]]:
    files = (
        get_files(pdir, accepted_tag_extensions, dirs2ignore, dirs2search)
        if tag_files is None
        else iter(tag_files)
    )
    dict_tag: Dict[str, Tuple[Path, int, str]] = {}
    for f in files:
        with open(f, "r") as fread:
            for i, line in enumerate(fread):
                tag = re.findall(CODE_RE_TAG, line)
                if len(tag) == 0:
                    continue
                elif len(tag) > 1:  # TODO allow this behaviour?
                    raise MultipleTagsInOneLine(
                        f"File {str(f)} has multiple tags on line {i + 1}"
                    )
                if tag[0] in dict_tag.keys():
                    raise TagAlreadyExistsError(
                        f"""Tag {tag[0]} already exists.
                    Earlier tag {dict_tag[tag[0]]}.
                    New tag found in {str(f)} on line {i + 1}."""
                    )
                dict_tag[tag[0]] = (f, i + 1, line.strip())

    return dict_tag


def replace_tags(
    pdir: Path,
    tags: Dict[str, Tuple[Path, int, str]],
    allow_not_found_tags: bool,
    accepted_ref_extensions: Optional[List[str]] = None,
    dirs2search: Optional[List[Path]] = None,
    dirs2ignore: Optional[List[Path]] = None,
    ref_files: Optional[List[Path]] = None,
):
    files = (
        get_files(pdir, accepted_ref_extensions, dirs2ignore, dirs2search)
        if ref_files is None
        else iter(ref_files)
    )
    for f in files:
        ref_found = False
        out_fpath = f.parent / f"{f.stem}{DOC_OUT_ID}{f.suffix}"
        with open(f, "r") as r_doc, open(out_fpath, "w") as w_doc:
            for line in r_doc:
                re_tags = re.finditer(DOC_REGEX_TAG, line)
                for re_tag in re_tags:
                    ref_found = True
                    tag, option = re_tag.group(1), re_tag.group(2)
                    if option is None and tag in tags.keys():
                        rep = tags[tag][0].name + " L" + str(tags[tag][1])
                    elif option == ":quote":
                        rep = tags[tag][2]
                    elif option == ":quotecode":
                        if tags[tag][0].suffix.lower() not in COMMENT_SYMBOL.keys():
                            warnings.warn(
                                f"{tags[tag][0].suffix} not recognised. Using :quote option"
                            )
                            rep = tags[tag][2]
                        else:
                            rep = re.sub(
                                rf"{COMMENT_SYMBOL[tags[tag][0].suffix.lower()]}.*$",
                                "",
                                tags[tag][2],
                            ).strip()
                    elif option == ":fulllinkline":
                        rep = tags[tag][0].as_posix() + "#L" + str(tags[tag][1])
                    elif option == ":fulllink":
                        rep = tags[tag][0].as_posix()
                    elif option == ":linkline":
                        rep = (
                            tags[tag][0].relative_to(pdir).as_posix()
                            + "#L"
                            + str(tags[tag][1])
                        )
                    elif option == ":link":
                        rep = tags[tag][0].relative_to(pdir).as_posix()
                    elif option == ":line":
                        rep = str(tags[tag][1])
                    elif option == ":file":
                        rep = tags[tag][0].name
                    elif option is not None and re.search(r"^:p+$", option) is not None:
                        rep = (
                            tags[tag][0].parent.relative_to(
                                tags[tag][0].parents[option.count("p")]
                            )
                            / tags[tag][0].name
                        ).as_posix()
                    elif allow_not_found_tags:
                        rep = UNKNOWN_ID
                    else:
                        raise TagNotFoundError(
                            f"Tag {tag} and keyword {option} not found. Possible Tags and keywords: {tags}"
                        )
                    line = re.sub(rf"{re_tag.group(0)}(?![a-zA-Z:])", rep, line)
                w_doc.write(line)
        if not ref_found:
            out_fpath.unlink()


def format_doc(
    rootdir: Optional[Union[str, Path]] = None,
    allow_not_found_tags: bool = False,
    accepted_tag_extensions: Optional[Union[str, List[str]]] = None,
    accepted_ref_extensions: Optional[Union[str, List[str]]] = None,
    dirs2ignore: Optional[Union[str, List[str], Path, List[Path]]] = None,
    dirs2search: Optional[Union[str, List[str], Path, List[Path]]] = None,
    tag_files: Optional[Union[str, List[str], Path, List[Path]]] = None,
    ref_files: Optional[Union[str, List[str], Path, List[Path]]] = None,
):
    """

    :param tag_files:
    :param ref_files:
    :param dirs2search:
    :param dirs2ignore:
    :param accepted_ref_extensions:
    :param accepted_tag_extensions:
    :param rootdir: root project folder
    :param allow_not_found_tags:
    :return:
    """

    # get root dir
    if rootdir is None:  # TODO follow pytest rootdir finding algorithm
        p = Path.cwd()
        while rootdir is None:
            if len(list(p.glob("pyproject.toml"))) == 1:
                rootdir = p
                break
            p = p.parent
            if p == Path(p.anchor) and len(list(p.glob("pyproject.toml"))) != 1:
                raise PyprojectNotFound(
                    f"Could not find pyproject.toml file in any directory in or higher than {str(Path.cwd())}"
                )
    elif rootdir == ".":
        rootdir = Path.cwd()
    else:
        rootdir = Path(rootdir)
        if not rootdir.is_absolute():
            rootdir = Path().cwd() / rootdir

    # pyproject. Inputs to function takes precedence
    pyproject_path = rootdir / "pyproject.toml"
    if pyproject_path.is_file():
        pyproject = toml.load(str(pyproject_path))
        if "refers_path" in pyproject["tool"][LIBRARY_NAME].keys():
            rootdir = Path(pyproject["tool"][LIBRARY_NAME]["refers_path"])
        if "allow_not_found_tags" in pyproject["tool"][LIBRARY_NAME].keys():
            allow_not_found_tags = pyproject["tool"][LIBRARY_NAME][
                "allow_not_found_tags"
            ]
        if (
            "dirs2ignore" in pyproject["tool"][LIBRARY_NAME].keys()
            and dirs2ignore is None
        ):
            dirs2ignore = [
                Path(f) for f in pyproject["tool"][LIBRARY_NAME]["dirs2ignore"]
            ]
        if (
            "dirs2search" in pyproject["tool"][LIBRARY_NAME].keys()
            and dirs2search is None
        ):
            dirs2search = [
                Path(f) for f in pyproject["tool"][LIBRARY_NAME]["dirs2search"]
            ]
        if "ref_files" in pyproject["tool"][LIBRARY_NAME].keys() and ref_files is None:
            ref_files = [Path(f) for f in pyproject["tool"][LIBRARY_NAME]["ref_files"]]
        if "tag_files" in pyproject["tool"][LIBRARY_NAME].keys() and tag_files is None:
            tag_files = [Path(f) for f in pyproject["tool"][LIBRARY_NAME]["tag_files"]]
        if (
            "accepted_tag_extensions" in pyproject["tool"][LIBRARY_NAME].keys()
            and accepted_tag_extensions is None
        ):
            accepted_tag_extensions = pyproject["tool"][LIBRARY_NAME][
                "accepted_mime_tag_types"
            ]
        if (
            "accepted_ref_extensions" in pyproject["tool"][LIBRARY_NAME].keys()
            and accepted_ref_extensions is None
        ):
            accepted_ref_extensions = pyproject["tool"][LIBRARY_NAME][
                "accepted_ref_extensions"
            ]

    # inputs (overrides pyproject)
    if isinstance(accepted_tag_extensions, str):
        accepted_tag_extensions = [accepted_tag_extensions]
    else:
        accepted_tag_extensions = [
            ".c",
            ".cpp",
            ".cs",
            ".go",
            ".html",
            ".java",
            ".js",
            ".py",
            ".ruby",
            ".sh",
            ".xml",
            ".txt",
            ".tex",
            ".md",
        ]
    if isinstance(accepted_ref_extensions, str):
        accepted_ref_extensions = [accepted_ref_extensions]
    else:
        accepted_ref_extensions = [
            ".c",
            ".cpp",
            ".cs",
            ".go",
            ".html",
            ".java",
            ".js",
            ".py",
            ".ruby",
            ".sh",
            ".xml",
            ".txt",
            ".tex",
            ".md",
        ]
    if isinstance(dirs2ignore, str):
        dirs2ignore = [Path(dirs2ignore)]
    elif isinstance(dirs2ignore, list) and isinstance(dirs2ignore[0], str):
        dirs2ignore = [Path(f) for f in dirs2ignore]
    else:
        dirs2ignore = None
    if isinstance(dirs2search, str):
        dirs2search = [Path(dirs2search)]
    elif isinstance(dirs2search, list) and isinstance(dirs2search[0], str):
        dirs2search = [Path(f) for f in dirs2search]
    else:
        dirs2search = None
    if isinstance(ref_files, str):
        ref_files = [Path(ref_files)]
    elif isinstance(ref_files, list) and isinstance(ref_files[0], str):
        ref_files = [Path(f) for f in ref_files]
    else:
        ref_files = None
    if isinstance(tag_files, str):
        tag_files = [Path(tag_files)]
    elif isinstance(tag_files, list) and isinstance(tag_files[0], str):
        tag_files = [Path(f) for f in tag_files]
    else:
        tag_files = None

    # get tags
    tags = get_tags(
        rootdir, accepted_tag_extensions, dirs2search, dirs2ignore, tag_files
    )

    # output document
    replace_tags(
        rootdir,
        tags,
        allow_not_found_tags,
        accepted_ref_extensions,
        dirs2search,
        dirs2ignore,
        ref_files,
    )
