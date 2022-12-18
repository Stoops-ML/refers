import re
from refers.refers import get_tags, format_doc, replace_tags
from pathlib import Path
import pytest
from refers.errors import (
    MultipleTagsInOneLine,
    TagAlreadyExistsError,
    TagNotFoundError,
    OptionNotFoundError,
)
from refers.definitions import COMMENT_SYMBOL


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.md",
                """# Test file

Function `f` has a comment: @tag:f_a:link and @tag:f_b:pp and @tag:f_c
            """,
            ),
        )
    ],
    indirect=True,
)
def test_tags_error_multiple_tags_one_line(create_tmp_file):
    with pytest.raises(MultipleTagsInOneLine):
        get_tags(Path().cwd(), tag_files=[create_tmp_file])


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
    a = 1  # @tag:a
    b = 1  # @tag:b
    c = 1
    d = 1  # @tag:a
""",
            ),
        )
    ],
    indirect=True,
)
def test_tags_error_tag_exists(create_tmp_file):
    with pytest.raises(TagAlreadyExistsError):
        get_tags(Path().cwd(), tag_files=[create_tmp_file])


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
e = (
1  # @tag:e
)
""",
            ),
        )
    ],
    indirect=True,
)
def test_tags_no_option(create_tmp_file):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])

    tag = tags.get_tag("a")
    assert tag.name == "a"
    assert tag.file.name == "test.py"
    assert tag.line_num == 2
    assert tag.line == tag.full_line == "a = 1  # @tag:a"

    tag = tags.get_tag("b")
    assert tag.name == "b"
    assert tag.file.name == "test.py"
    assert tag.line_num == 3
    assert tag.line == tag.full_line == "b = 1  # @tag:b"

    tag = tags.get_tag("d")
    assert tag.name == "d"
    assert tag.file.name == "test.py"
    assert tag.line_num == 5
    assert tag.line == tag.full_line == "d = 1  # @tag:d"

    tag = tags.get_tag("e")
    assert tag.name == "e"
    assert tag.file.name == "test.py"
    assert tag.line_num == 7
    assert tag.line == "1  # @tag:e"
    assert tag.full_line == "e = 1  # @tag:e"  # black'd


@pytest.mark.parametrize(
    "check_refers_test_files",
    [
        (
            (
                "file_with_refs.md",
                """# Test file
Function `f` has a comment: @ref:f_a:link and  and @ref:f_a
Function `f` has a comment: @ref:f_a:line in the [file](@ref:f_a:link) and  and @ref:f_a and @ref:f_a:quotecode
""",
            ),
            (
                "file_with_tags.py",
                """def f():
    a = 1  # @tag:f_a this is a comment
    return a
def f1():
    a = 1  # @tag:a this is a comment
    return a
def f2():
    b = 1  # @tag:b this is a comment
    return a
def f3():
    a = 1  # @tag:d this is a comment
    return a
""",
            ),
            (
                "file_no_refs.py",
                "This is a test file with no refs",
            ),
        ),
    ],
    indirect=True,
)
def test_format_doc_full_path_str(check_refers_test_files: Path):
    format_doc(str(check_refers_test_files))


@pytest.mark.parametrize(
    "check_refers_test_files",
    [
        (
            (
                "file_with_refs.md",
                """# Test file
Function `f` has a comment: @ref:f_a:link and  and @ref:f_a
Function `f` has a comment: @ref:f_a:line in the [file](@ref:f_a:link) and  and @ref:f_a and @ref:f_a:quotecode
""",
            ),
            (
                "file_with_tags.py",
                """def f():
    a = 1  # @tag:f_a this is a comment
    return a
def f1():
    a = 1  # @tag:a this is a comment
    return a
def f2():
    b = 1  # @tag:b this is a comment
    return a
def f3():
    a = 1  # @tag:d this is a comment
    return a
""",
            ),
            (
                "file_no_refs.py",
                "This is a test file with no refs",
            ),
        ),
    ],
    indirect=True,
)
def test_format_doc_full_path(check_refers_test_files: Path):
    format_doc(check_refers_test_files)


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.jl",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.c",
                """# Test file
a = 1  // @tag:a
b = 1  // @tag:b
c = 1
d = 1  // @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.cpp",
                """# Test file
a = 1  // @tag:a
b = 1  // @tag:b
c = 1
d = 1  // @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.cs",
                """# Test file
a = 1  // @tag:a
b = 1  // @tag:b
c = 1
d = 1  // @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.java",
                """# Test file
a = 1  // @tag:a
b = 1  // @tag:b
c = 1
d = 1  // @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.js",
                """# Test file
a = 1  // @tag:a
b = 1  // @tag:b
c = 1
d = 1  // @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.go",
                """# Test file
a = 1  // @tag:a
b = 1  // @tag:b
c = 1
d = 1  // @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.html",
                """# Test file
a = 1  <! -- @tag:a
b = 1  <! -- @tag:b
c = 1
d = 1  <! -- @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.sh",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.ruby",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.csh",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.xml",
                """# Test file
a = 1  /// @tag:a
b = 1  /// @tag:b
c = 1
d = 1  /// @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.tex",
                """# Test file
a = 1  % @tag:a
b = 1  % @tag:b
c = 1
d = 1  % @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
        (
            (
                "test.m",
                """# Test file
a = 1  % @tag:a
b = 1  % @tag:b
c = 1
d = 1  % @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline""",
            ),
        ),
    ],
    indirect=True,
)
def test_replace_tags(create_tmp_file: Path):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])
    replace_tags(
        create_tmp_file.parent,
        tags,
        False,
        [".md"],
    )
    comment = COMMENT_SYMBOL[create_tmp_file.suffix]
    ans = f"# Test file\nOn line [2](test{create_tmp_file.suffix}#L2) the code has a = 1. This is it's link: test{create_tmp_file.suffix}.\n`b` appears in test{create_tmp_file.suffix} L3, is located {create_tmp_file.parent.as_posix()}/test{create_tmp_file.suffix} and has contents: b = 1  {comment} @tag:b.\n`d` appears in file test{create_tmp_file.suffix}, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is {create_tmp_file.parent.as_posix()}/test{create_tmp_file.suffix}#L5"
    refers_file = create_tmp_file.parent / "test_refers.md"
    with open(refers_file, "r") as f:
        assert ans == f.read()


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline
There is no tag for 'c': @ref:c""",
            ),
        )
    ],
    indirect=True,
)
def test_replace_tags_allow_unknown_tags(create_tmp_file: Path):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])
    replace_tags(
        create_tmp_file.parent,
        tags,
        True,
        [".md"],
    )
    comment = COMMENT_SYMBOL[create_tmp_file.suffix]
    ans = f"# Test file\nOn line [2](test{create_tmp_file.suffix}#L2) the code has a = 1. This is it's link: test{create_tmp_file.suffix}.\n`b` appears in test{create_tmp_file.suffix} L3, is located {create_tmp_file.parent.as_posix()}/test{create_tmp_file.suffix} and has contents: b = 1  {comment} @tag:b.\n`d` appears in file test{create_tmp_file.suffix}, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is {create_tmp_file.parent.as_posix()}/test{create_tmp_file.suffix}#L5\nThere is no tag for 'c': TAG-NOT-FOUND"
    refers_file = create_tmp_file.parent / "test_refers.md"
    with open(refers_file, "r") as f:
        assert ans == f.read()


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline
There is no tag for 'c': @ref:c""",
            ),
        )
    ],
    indirect=True,
)
def test_replace_tags_tag_not_found(create_tmp_file):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])
    with pytest.raises(TagNotFoundError) as exc_info:  # c tag not found
        replace_tags(
            create_tmp_file.parent,
            tags,
            False,
            [".md"],
        )
        assert (
            re.search(r"^Tag c and keyword  not found\.", str(exc_info.value))
            is not None
        )


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line1](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline
There is no tag for 'c': @ref:c""",
            ),
        )
    ],
    indirect=True,
)
def test_replace_tags_option_not_found(create_tmp_file):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])
    with pytest.raises(OptionNotFoundError) as exc_info:  # c tag not found
        replace_tags(
            create_tmp_file.parent,
            tags,
            False,
            [".md"],
        )
        assert (
            re.search(r"^Tag c and keyword  not found\.", str(exc_info.value))
            is not None
        )


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file
a = 1  # @tag:a
b = 1  # @tag:b
c = 1
d = 1  # @tag:d
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line1](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline
There is no tag for 'c': @ref:c""",
            ),
        )
    ],
    indirect=True,
)
def test_replace_tags_delete_file_on_error(create_tmp_file: Path):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])
    with pytest.raises(OptionNotFoundError):
        replace_tags(
            create_tmp_file.parent,
            tags,
            False,
            [".md"],
        )
    f_refers = create_tmp_file.parent / "".join(
        (create_tmp_file.stem, "_refers", create_tmp_file.suffix)
    )
    assert not f_refers.is_file()
