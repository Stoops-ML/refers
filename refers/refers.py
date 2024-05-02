import re
from pathlib import Path
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union

import black
import toml
from black import nodes
from black.parsing import lib2to3_parse
from blib2to3.pytree import Leaf
from blib2to3.pytree import Node

from refers.compromise_black import LineGenerator
from refers.definitions import CODE_RE_TAG
from refers.definitions import DOC_OUT_ID
from refers.definitions import DOC_RE_TAG
from refers.definitions import LIBRARY_NAME
from refers.errors import MultipleTagsInOneLine
from refers.errors import OptionNotFoundError
from refers.errors import PyprojectNotFound
from refers.errors import TagNotFoundError
from refers.tags import Tag
from refers.tags import Tags

# types
T = TypeVar("T")
Index = int
LeafID = int

LN = Union[Leaf, Node]


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
        with open(f) as fread:
            if not f.suffix == ".py":
                for i, full_line in enumerate(fread):
                    full_line = full_line.strip()
                    line_num = i + 1
                    tag_names = re.findall(CODE_RE_TAG, full_line)
                    if len(tag_names) == 0:
                        continue
                    elif len(tag_names) > 1:
                        raise MultipleTagsInOneLine
                    tag_name = tag_names[0]
                    tag = Tag(
                        tag_name,
                        line_num,
                        full_line,
                        f,
                        line_num,
                        line_num,
                        full_line,
                        Node(256, []),
                    )
                    tags.add_tag(tag)
            else:
                src_lines = fread.readlines()
                fread.seek(0)
                src_contents = fread.read()
                src_node = lib2to3_parse(src_contents.lstrip(), mode.target_versions)
                lines = LineGenerator(mode=mode)
                for current_line in lines.visit(src_node):
                    # standalone comments hold no information in Leaf and is therefore not supported
                    if current_line.leaves[0].type == nodes.STANDALONE_COMMENT:
                        continue

                    line_num_start = current_line.leaves[0].get_lineno()
                    line_num_end = current_line.leaves[-1].get_lineno()
                    full_line = "".join(src_lines[line_num_start - 1 : line_num_end])
                    full_line = re.sub(
                        r"^\s*(.*)\n$", r"\1", full_line, flags=re.DOTALL
                    )

                    for line_num in range(line_num_start, line_num_end + 1):
                        src_line = re.sub(
                            r"\s*(.*)\n$", r"\1", src_lines[line_num - 1]
                        )  # strip newline
                        tag_names = re.findall(CODE_RE_TAG, src_line)
                        if len(tag_names) == 0:
                            continue
                        elif len(tag_names) > 1:
                            raise MultipleTagsInOneLine
                        tag = Tag(
                            tag_names[0],
                            line_num,
                            src_line,
                            f,
                            line_num_start,
                            line_num_end,
                            full_line,
                            current_line.leaves[0].parent,
                        )
                        tags.add_tag(tag)
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
            with open(f) as r_doc, open(out_fpath, "w") as w_doc:
                for line in r_doc:
                    re_tags = re.finditer(DOC_RE_TAG, line)
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
        if LIBRARY_NAME in pyproject["tool"].keys():
            inputs_to_change = pyproject["tool"][LIBRARY_NAME].keys()
            if "refers_path" in inputs_to_change:
                rootdir_tmp = Path(pyproject["tool"][LIBRARY_NAME]["refers_path"])
                if rootdir_tmp.exists():
                    rootdir = rootdir_tmp
                else:  # refers_path is defined in relation to pyproject_path
                    rootdir = rootdir / rootdir_tmp
            if "allow_not_found_tags" in inputs_to_change:
                allow_not_found_tags = pyproject["tool"][LIBRARY_NAME][
                    "allow_not_found_tags"
                ]
            if "dirs2ignore" in inputs_to_change and dirs2ignore is None:
                dirs2ignore = [
                    Path(f) for f in pyproject["tool"][LIBRARY_NAME]["dirs2ignore"]
                ]
            if "dirs2search" in inputs_to_change and dirs2search is None:
                dirs2search = [
                    Path(f) for f in pyproject["tool"][LIBRARY_NAME]["dirs2search"]
                ]
            if "ref_files" in inputs_to_change and ref_files is None:
                ref_files = [
                    Path(f) for f in pyproject["tool"][LIBRARY_NAME]["ref_files"]
                ]
            if "tag_files" in inputs_to_change and tag_files is None:
                tag_files = [
                    Path(f) for f in pyproject["tool"][LIBRARY_NAME]["tag_files"]
                ]
            if (
                "accepted_tag_extensions" in inputs_to_change
                and accepted_tag_extensions is None
            ):
                accepted_tag_extensions = pyproject["tool"][LIBRARY_NAME][
                    "accepted_tag_extensions"
                ]
            if (
                "accepted_ref_extensions" in inputs_to_change
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

    # checks
    if not rootdir.exists():
        raise ValueError(f"The root directory does not exist: {rootdir}.")
    if dirs2search is not None:
        for d in dirs2search:
            if not d.exists():
                raise ValueError(
                    f"The following directory which was requested to be searched does not exist: {d}."
                )

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
