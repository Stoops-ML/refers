import re
from pathlib import Path

import pytest

from refers.definitions import COMMENT_SYMBOL
from refers.errors import MultipleTagsInOneLine
from refers.errors import OptionNotFoundError
from refers.errors import TagAlreadyExistsError
from refers.errors import TagNotFoundError
from refers.refers import format_doc
from refers.refers import get_tags
from refers.refers import replace_tags


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
    assert (
        tag.full_line
        == """e = (
1  # @tag:e
)"""
    )


@pytest.mark.parametrize(
    "create_tmp_file",
    [
        (
            (
                "test.py",
                """# Test file       
a = 1  # note before tag @tag:a note after tag
b =  1 # @tag:b note after tag
# standalone comment
c = 1
d =1  # note before tag @tag:d
e = ( # @tag:fe
1 # note whitespace after  @tag:e  
)#note whitespace after tag@tag:ef 
# standalone comment
f = (
1 # comment
# standalone comment 
)  # @tag:f  
# standalone comment
f=1
                
def f():
    a = 1  # @tag:aa
    return a


class F():
    a = 1  # @tag:bb
         
""",  # noqa
            ),
        )
    ],
    indirect=True,
)
def test_tags_hard_cases(create_tmp_file):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])

    tag = tags.get_tag("a")
    assert tag.name == "a"
    assert tag.file.name == "test.py"
    assert tag.line_num == 2
    assert tag.line == tag.full_line == "a = 1  # note before tag @tag:a note after tag"

    tag = tags.get_tag("b")
    assert tag.name == "b"
    assert tag.file.name == "test.py"
    assert tag.line_num == 3
    assert tag.line == tag.full_line == "b =  1 # @tag:b note after tag"

    tag = tags.get_tag("d")
    assert tag.name == "d"
    assert tag.file.name == "test.py"
    assert tag.line_num == 6
    assert tag.line == tag.full_line == "d =1  # note before tag @tag:d"

    tag = tags.get_tag("e")
    assert tag.name == "e"
    assert tag.file.name == "test.py"
    assert tag.line_num == 8
    assert tag.line_num_start == 7
    assert tag.line_num_end == 9
    assert tag.line == "1 # note whitespace after  @tag:e  "
    assert (
        tag.full_line
        == """e = ( # @tag:fe
1 # note whitespace after  @tag:e  
)#note whitespace after tag@tag:ef """  # noqa
    )

    tag = tags.get_tag("fe")
    assert tag.name == "fe"
    assert tag.file.name == "test.py"
    assert tag.line_num == 7
    assert tag.line_num_start == 7
    assert tag.line == "e = ( # @tag:fe"
    assert tag.line_num_end == 9
    assert (
        tag.full_line
        == """e = ( # @tag:fe
1 # note whitespace after  @tag:e  
)#note whitespace after tag@tag:ef """  # noqa
    )

    tag = tags.get_tag("ef")
    assert tag.name == "ef"
    assert tag.file.name == "test.py"
    assert tag.line_num == 9
    assert tag.line_num_start == 7
    assert tag.line_num_end == 9
    assert tag.line == ")#note whitespace after tag@tag:ef "
    assert (
        tag.full_line
        == """e = ( # @tag:fe
1 # note whitespace after  @tag:e  
)#note whitespace after tag@tag:ef """  # noqa
    )

    tag = tags.get_tag("f")
    assert tag.name == "f"
    assert tag.file.name == "test.py"
    assert tag.line_num == 14
    assert tag.line_num_start == 11
    assert tag.line_num_end == 14
    assert tag.line == ")  # @tag:f  "
    assert (
        tag.full_line
        == """f = (
1 # comment
# standalone comment 
)  # @tag:f  """  # noqa
    )

    tag = tags.get_tag("aa")
    assert tag.name == "aa"
    assert tag.file.name == "test.py"
    assert tag.line_num == 19
    assert tag.line == tag.full_line == "a = 1  # @tag:aa"
    assert tag.func_name == "f"
    assert tag.class_name is None

    tag = tags.get_tag("bb")
    assert tag.name == "bb"
    assert tag.file.name == "test.py"
    assert tag.line_num == 24
    assert tag.line == tag.full_line == "a = 1  # @tag:bb"
    assert tag.func_name is None
    assert tag.class_name == "F"


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
                "# This is a test file with no refs",
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
                "# This is a test file with no refs",
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
    with open(refers_file) as f:
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
def func1():
    return 1#@tag:f
class A(object):
    def __init__(self):
        pass#@tag:A
def func2():
    def func3():# @tag:func3a
        return 2# @tag:func3b
""",
            ),
            (
                "test.md",
                """# Test file
On line [@ref:a:line](@ref:a:linkline) the code has @ref:a:quotecode. This is it's link: @ref:a:link.
`b` appears in @ref:b, is located @ref:b:fulllink and has contents: @ref:b:quote.
`d` appears in file @ref:d:file, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is @ref:d:fulllinkline
There is one class @ref:A:class, a function @ref:f:func, and a nested function @ref:func3a:func (== @ref:func3b:func)""",
            ),
        )
    ],
    indirect=True,
)
def test_replace_tags_with_class_and_functions(create_tmp_file: Path):
    tags = get_tags(Path().cwd(), tag_files=[create_tmp_file])
    replace_tags(
        create_tmp_file.parent,
        tags,
        False,
        [".md"],
    )
    comment = COMMENT_SYMBOL[create_tmp_file.suffix]
    ans = f"# Test file\nOn line [2](test{create_tmp_file.suffix}#L2) the code has a = 1. This is it's link: test{create_tmp_file.suffix}.\n`b` appears in test{create_tmp_file.suffix} L3, is located {create_tmp_file.parent.as_posix()}/test{create_tmp_file.suffix} and has contents: b = 1  {comment} @tag:b.\n`d` appears in file test{create_tmp_file.suffix}, which has a relative path one parent up of  and a relative path three parents up of . The full link with line is {create_tmp_file.parent.as_posix()}/test{create_tmp_file.suffix}#L5\nThere is one class A, a function func1, and a nested function func3 (== func3)"
    refers_file = create_tmp_file.parent / "test_refers.md"
    with open(refers_file) as f:
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
    with open(refers_file) as f:
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
    assert "Tag c not found" == str(exc_info.value)


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
