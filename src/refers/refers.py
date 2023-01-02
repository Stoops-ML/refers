from black.linegen import LineGenerator
from typing import (
    List,
    Optional,
    TypeVar,
    Union,
)

from blib2to3.pytree import Node, Leaf  # type: ignore

LN = Union[Leaf, Node]
T = TypeVar("T")
from refers.tags import Tag, Tags


from black.comments import normalize_fmt_off
import black
from black.parsing import lib2to3_parse

import warnings
from refers.errors import (
    MultipleTagsInOneLine,
    TagNotFoundError,
    PyprojectNotFound,
    OptionNotFoundError,
)
import re
from pathlib import Path
from refers.definitions import (
    CODE_RE_TAG,
    DOC_REGEX_TAG,
    DOC_OUT_ID,
    LIBRARY_NAME,
)
import toml


def numpy2latex(
    numpy_str: str, use_times_sign: bool = False, use_divide_sign: bool = False
) -> str:
    """

    Methodology:
    - catch characters in brackets using [^)]
    - use non-greedy catch .+?
    - place spaces around replaced strings so that word-non-word boundaries \b can be used
    - only kwargs are removed from inputs to functions

    :param use_divide_sign:
    :param numpy_str:
    :param use_times_sign:
    :return:
    """
    # formatting
    numpy_str = re.sub("[ _]", "", numpy_str)
    numpy_str = re.sub(r"numpy\.", "np.", numpy_str)
    numpy_str = re.sub(r"\[[^]]*?\]", "", numpy_str)
    numpy_str = re.sub(
        r"\b\(([^)]+?)(?:,\w+=[^)]+?)+\)", r"(\1)", numpy_str
    )  # remove kwargs

    # operators
    numpy_str = re.sub(r"!=", r" \\neq ", numpy_str)
    numpy_str = re.sub(r"<=", r" \\leq ", numpy_str)
    numpy_str = re.sub(r">=", r" \\geq ", numpy_str)
    numpy_str = re.sub(r"\*\*", " ^ ", numpy_str)
    numpy_str = (
        re.sub(r"\*", r" \times ", numpy_str)
        if use_times_sign
        else re.sub(r"\*", "", numpy_str)
    )
    if not use_divide_sign:
        numpy_str = re.sub(
            r"(\bnp\.\w+)?\(([^)]+?)\)/(\bnp\.\w+)?\(([^)]+?)\)",
            r" \\frac{\1(\2)}{\3(\4)} ",
            numpy_str,
        )
        numpy_str = re.sub(
            r"(\w+)/(\bnp\.\w+)?\(([^)]+?)\)", r" \\frac{\1}{\2(\3)} ", numpy_str
        )
        numpy_str = re.sub(
            r"(\bnp\.\w+)?\(([^)]+?)\)/(\w+)", r" \\frac{\1(\2)}{\3} ", numpy_str
        )
        numpy_str = re.sub(r"(\w+)/(\w+)", r" \\frac{\1}{\2} ", numpy_str)
    else:
        numpy_str = re.sub(r"/", r" \\div ", numpy_str)

    # functions
    numpy_str = re.sub(
        r"\bnp\.dot\(([^)]+?),([^)]+?)(,?[^)]*?)\)", r" \1\\cdot \2 ", numpy_str
    )
    numpy_str = re.sub(
        r"\bnp\.cross\(([^)]+?),([^)]+?)(,?[^)]*?)\)", r" \1\\times \2 ", numpy_str
    )
    numpy_str = re.sub(
        r"\bnp\.(\w+)\(([^)]+?)\)", r" \\\1{\2} ", numpy_str
    )  # general function

    # letters
    numpy_str = re.sub(r"\b([a|A]lpha)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([o|O]mega)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([b|B]eta)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([g|G]amma)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([l|L]amba)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([m|M]u)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([n|N]u)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([x|X]i)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([o|O]micron)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([d|D]elta)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([t|T]au)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([u|U]psilon)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([d|D]igamma)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([z|Z]eta)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b([i|I]ota)\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([r|R]ho))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([s|S]igma))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([p|P]i))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([p|P]hi))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([p|P]si))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([c|C]hi))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([e|E]psilon))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([t|T]heta))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\b((?:var)?([k|K]appa))\b", r" \\\1 ", numpy_str)
    numpy_str = re.sub(r"\binfinity\b", r" \\infty ", numpy_str)

    # clean up
    numpy_str = re.sub(
        r"{\(([^)]+?)\)}", r"{\1}", numpy_str
    )  # remove unnecessary brackets
    numpy_str = re.sub(r" ", "", numpy_str)

    return numpy_str


def get_tag_name(line: str) -> str:
    tag_names = re.findall(CODE_RE_TAG, line)
    if len(tag_names) == 0:
        raise TagNotFoundError
    elif len(tag_names) > 1:
        raise MultipleTagsInOneLine
    return tag_names[0]


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
) -> Tags:
    files = (
        get_files(pdir, accepted_tag_extensions, dirs2ignore, dirs2search)
        if tag_files is None
        else iter(tag_files)
    )
    mode = black.Mode()
    tags = Tags()
    for f in files:
        tag_found = False
        with open(f, "r") as fread:
            for i, line in enumerate(fread):
                line = line.strip()
                line_num = i + 1
                tag_name = get_tag_name(line)
                tag_found = True
                tag = Tag(
                    tag_name, line_num, line, f, 0, 0, line
                )  # TODO get start, end line numbers
                tags.add_tag(tag)

            if f.suffix == ".py" and tag_found:
                try:
                    fread.seek(0)
                    src_contents = fread.read()
                    src_node = lib2to3_parse(
                        src_contents.lstrip(), mode.target_versions
                    )
                    normalize_fmt_off(src_node, preview=mode.preview)
                    lines = LineGenerator(mode=mode)
                    for current_line in lines.visit(
                        src_node
                    ):  # TODO monkeypatch lines.visit to return start and end line numbers. Also remove above for loop and rely only on this one
                        line = str(current_line)  # black'd
                        tag_name = get_tag_name(line)
                        tag = tags.get_tag(tag_name)
                        tag.full_line = line.strip()
                except black.parsing.InvalidInput:
                    warnings.warn(
                        f"Cannot parse file {str(f)} with black. Full line is line."
                    )
    return tags


def replace_tags(
    pdir: Path,
    tags: Tags,
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
        try:
            with open(f, "r") as r_doc, open(out_fpath, "w") as w_doc:
                for line in r_doc:
                    re_tags = re.finditer(DOC_REGEX_TAG, line)
                    for re_tag in re_tags:
                        ref_found = True
                        tag_name, option = re_tag.group(1), re_tag.group(2)
                        if option is None:
                            option = ":default"

                        try:
                            tag = tags.get_tag(tag_name)
                        except TagNotFoundError as e:
                            if allow_not_found_tags:
                                option = ":unknown_tag"
                            else:
                                raise e

                        # replace ref with tag:option
                        visit = getattr(tag, f"visit_{option[1:]}", None)
                        if visit is None:
                            visits = [
                                func.replace("visit_", "")
                                for func in dir(Tag)
                                if (callable(getattr(Tag, func)) and "visit_" in func)
                            ]
                            raise OptionNotFoundError(
                                f"Option {option} of tag {tag_name} not found. Possible options: {visits}"
                            )
                        else:
                            kwargs = {"parent_dir": pdir}
                            line = re.sub(
                                rf"{re_tag.group(0)}(?![a-zA-Z:])",
                                visit(**kwargs),
                                line,
                            )
                    w_doc.write(line)
            if not ref_found:
                out_fpath.unlink()
        except Exception as e:
            out_fpath.unlink()
            raise e


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

    # get root dir TODO use find_root_project() from black: https://github.com/psf/black/blob/d97b7898b34b67eb3c6839998920e17ac8c77908/src/black/files.py#L43
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
        if LIBRARY_NAME not in pyproject["tool"].keys():
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
            if (
                "ref_files" in pyproject["tool"][LIBRARY_NAME].keys()
                and ref_files is None
            ):
                ref_files = [
                    Path(f) for f in pyproject["tool"][LIBRARY_NAME]["ref_files"]
                ]
            if (
                "tag_files" in pyproject["tool"][LIBRARY_NAME].keys()
                and tag_files is None
            ):
                tag_files = [
                    Path(f) for f in pyproject["tool"][LIBRARY_NAME]["tag_files"]
                ]
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
