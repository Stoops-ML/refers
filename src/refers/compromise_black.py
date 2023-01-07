"""sorry black, you've been compromised"""
import itertools
import sys
from dataclasses import dataclass
from functools import partial
from typing import (
    Callable,
    Dict,
    Iterator,
    Sequence,
    Tuple,
    TypeVar,
    cast,
)
from typing import Set

from black.brackets import BracketTracker
from black.comments import generate_comments
from black.lines import enumerate_reversed
from black.mode import Mode, Preview
from black.nodes import ASSIGNMENTS
from black.nodes import CLOSING_BRACKETS
from black.nodes import STANDALONE_COMMENT, TEST_DESCENDANTS
from black.nodes import Visitor
from black.nodes import WHITESPACE, STATEMENT
from black.nodes import is_multiline_string, is_import, is_type_comment
from black.nodes import is_name_token
from black.nodes import is_one_sequence_between
from black.nodes import is_stub_suite, is_stub_body
from black.nodes import syms, child_towards

# types
T = TypeVar("T")
Index = int
LeafID = int


from dataclasses import field
from black.nodes import BRACKETS
from blib2to3.pgen2 import token

from typing import (
    List,
    Optional,
    Union,
)

from blib2to3.pytree import Node, Leaf  # type: ignore
from black.linegen import normalize_prefix

LN = Union[Leaf, Node]


@dataclass
class Line:
    """redefine to:
        1. include parent nodes of leaves that make up line

    Original docstring:
    Holds leaves and comments. Can be printed with `str(line)`."""

    mode: Mode
    depth: int = 0
    leaves: List[Leaf] = field(default_factory=list)
    parent_nodes: List[Node] = field(default_factory=list)
    # keys ordered like `leaves`
    comments: Dict[LeafID, List[Leaf]] = field(default_factory=dict)
    bracket_tracker: BracketTracker = field(default_factory=BracketTracker)
    inside_brackets: bool = False
    should_split_rhs: bool = False
    magic_trailing_comma: Optional[Leaf] = None

    def append(self, leaf: Leaf, preformatted: bool = False) -> None:
        """Add a new `leaf` to the end of the line.

        Unless `preformatted` is True, the `leaf` will receive a new consistent
        whitespace prefix and metadata applied by :class:`BracketTracker`.
        Trailing commas are maybe removed, unpacked for loop variables are
        demoted from being delimiters.

        Inline comments are put aside.
        """
        has_value = leaf.type in BRACKETS or bool(leaf.value.strip())
        if not has_value:
            return

        if token.COLON == leaf.type and self.is_class_paren_empty:
            del self.leaves[-2:]
            del self.parent_nodes[-2:]
        # if self.leaves and not preformatted:
        # Note: at this point leaf.prefix should be empty except for
        # imports, for which we only preserve newlines.
        # leaf.prefix += whitespace(
        #     leaf, complex_subscript=self.is_complex_subscript(leaf)
        # )
        if self.inside_brackets or not preformatted:
            self.bracket_tracker.mark(leaf)
            # if self.mode.magic_trailing_comma:
            #     if self.has_magic_trailing_comma(leaf):
            #         self.magic_trailing_comma = leaf
            # elif self.has_magic_trailing_comma(leaf, ensure_removable=True):
            #     self.remove_trailing_comma()
        if not self.append_comment(leaf):
            self.leaves.append(leaf)
            self.parent_nodes.append(leaf.parent)

    def append_safe(self, leaf: Leaf, preformatted: bool = False) -> None:
        """Like :func:`append()` but disallow invalid standalone comment structure.

        Raises ValueError when any `leaf` is appended after a standalone comment
        or when a standalone comment is not the first leaf on the line.
        """
        if self.bracket_tracker.depth == 0:
            if self.is_comment:
                raise ValueError("cannot append to standalone comments")

            if self.leaves and leaf.type == STANDALONE_COMMENT:
                raise ValueError(
                    "cannot append standalone comments to a populated line"
                )

        self.append(leaf, preformatted=preformatted)

    @property
    def is_comment(self) -> bool:
        """Is this line a standalone comment?"""
        return len(self.leaves) == 1 and self.leaves[0].type == STANDALONE_COMMENT

    @property
    def is_decorator(self) -> bool:
        """Is this line a decorator?"""
        return bool(self) and self.leaves[0].type == token.AT

    @property
    def is_import(self) -> bool:
        """Is this an import line?"""
        return bool(self) and is_import(self.leaves[0])

    @property
    def is_class(self) -> bool:
        """Is this line a class definition?"""
        return (
            bool(self)
            and self.leaves[0].type == token.NAME
            and self.leaves[0].value == "class"
        )

    @property
    def is_stub_class(self) -> bool:
        """Is this line a class definition with a body consisting only of "..."?"""
        return self.is_class and self.leaves[-3:] == [
            Leaf(token.DOT, ".") for _ in range(3)
        ]

    @property
    def is_def(self) -> bool:
        """Is this a function definition? (Also returns True for async defs.)"""
        try:
            first_leaf = self.leaves[0]
        except IndexError:
            return False

        try:
            second_leaf: Optional[Leaf] = self.leaves[1]
        except IndexError:
            second_leaf = None
        return (first_leaf.type == token.NAME and first_leaf.value == "def") or (
            first_leaf.type == token.ASYNC
            and second_leaf is not None
            and second_leaf.type == token.NAME
            and second_leaf.value == "def"
        )

    @property
    def is_class_paren_empty(self) -> bool:
        """Is this a class with no base classes but using parentheses?

        Those are unnecessary and should be removed.
        """
        return (
            bool(self)
            and len(self.leaves) == 4
            and self.is_class
            and self.leaves[2].type == token.LPAR
            and self.leaves[2].value == "("
            and self.leaves[3].type == token.RPAR
            and self.leaves[3].value == ")"
        )

    @property
    def is_triple_quoted_string(self) -> bool:
        """Is the line a triple quoted string?"""
        return (
            bool(self)
            and self.leaves[0].type == token.STRING
            and self.leaves[0].value.startswith(('"""', "'''"))
        )

    @property
    def opens_block(self) -> bool:
        """Does this line open a new level of indentation."""
        if len(self.leaves) == 0:
            return False
        return self.leaves[-1].type == token.COLON

    def contains_standalone_comments(self, depth_limit: int = sys.maxsize) -> bool:
        """If so, needs to be split before emitting."""
        for leaf in self.leaves:
            if leaf.type == STANDALONE_COMMENT and leaf.bracket_depth <= depth_limit:
                return True

        return False

    def contains_uncollapsable_type_comments(self) -> bool:
        ignored_ids = set()
        try:
            last_leaf = self.leaves[-1]
            ignored_ids.add(id(last_leaf))
            if last_leaf.type == token.COMMA or (
                last_leaf.type == token.RPAR and not last_leaf.value
            ):
                # When trailing commas or optional parens are inserted by Black for
                # consistency, comments after the previous last element are not moved
                # (they don't have to, rendering will still be correct).  So we ignore
                # trailing commas and invisible.
                last_leaf = self.leaves[-2]
                ignored_ids.add(id(last_leaf))
        except IndexError:
            return False

        # A type comment is uncollapsable if it is attached to a leaf
        # that isn't at the end of the line (since that could cause it
        # to get associated to a different argument) or if there are
        # comments before it (since that could cause it to get hidden
        # behind a comment.
        comment_seen = False
        for leaf_id, comments in self.comments.items():
            for comment in comments:
                if is_type_comment(comment):
                    if comment_seen or (
                        not is_type_comment(comment, " ignore")
                        and leaf_id not in ignored_ids
                    ):
                        return True

                comment_seen = True

        return False

    def contains_unsplittable_type_ignore(self) -> bool:
        if not self.leaves:
            return False

        # If a 'type: ignore' is attached to the end of a line, we
        # can't split the line, because we can't know which of the
        # subexpressions the ignore was meant to apply to.
        #
        # We only want this to apply to actual physical lines from the
        # original source, though: we don't want the presence of a
        # 'type: ignore' at the end of a multiline expression to
        # justify pushing it all onto one line. Thus we
        # (unfortunately) need to check the actual source lines and
        # only report an unsplittable 'type: ignore' if this line was
        # one line in the original code.

        # Grab the first and last line numbers, skipping generated leaves
        first_line = next((leaf.lineno for leaf in self.leaves if leaf.lineno != 0), 0)
        last_line = next(
            (leaf.lineno for leaf in reversed(self.leaves) if leaf.lineno != 0), 0
        )

        if first_line == last_line:
            # We look at the last two leaves since a comma or an
            # invisible paren could have been added at the end of the
            # line.
            for node in self.leaves[-2:]:
                for comment in self.comments.get(id(node), []):
                    if is_type_comment(comment, " ignore"):
                        return True

        return False

    def contains_multiline_strings(self) -> bool:
        return any(is_multiline_string(leaf) for leaf in self.leaves)

    def has_magic_trailing_comma(
        self, closing: Leaf, ensure_removable: bool = False
    ) -> bool:
        """Return True if we have a magic trailing comma, that is when:
        - there's a trailing comma here
        - it's not a one-tuple
        - it's not a single-element subscript
        Additionally, if ensure_removable:
        - it's not from square bracket indexing
        """
        if not (
            closing.type in CLOSING_BRACKETS
            and self.leaves
            and self.leaves[-1].type == token.COMMA
        ):
            return False

        if closing.type == token.RBRACE:
            return True

        if closing.type == token.RSQB:
            if (
                Preview.one_element_subscript in self.mode
                and closing.parent
                and closing.parent.type == syms.trailer
                and closing.opening_bracket
                and is_one_sequence_between(
                    closing.opening_bracket,
                    closing,
                    self.leaves,
                    brackets=(token.LSQB, token.RSQB),
                )
            ):
                return False

            if not ensure_removable:
                return True
            comma = self.leaves[-1]
            return bool(comma.parent and comma.parent.type == syms.listmaker)

        if self.is_import:
            return True

        if closing.opening_bracket is not None and not is_one_sequence_between(
            closing.opening_bracket, closing, self.leaves
        ):
            return True

        return False

    def append_comment(self, comment: Leaf) -> bool:
        """Add an inline or standalone comment to the line."""
        if (
            comment.type == STANDALONE_COMMENT
            and self.bracket_tracker.any_open_brackets()
        ):
            comment.prefix = ""
            return False

        if comment.type != token.COMMENT:
            return False

        if not self.leaves:
            comment.type = STANDALONE_COMMENT
            comment.prefix = ""
            return False

        last_leaf = self.leaves[-1]
        if (
            last_leaf.type == token.RPAR
            and not last_leaf.value
            and last_leaf.parent
            and len(list(last_leaf.parent.leaves())) <= 3
            and not is_type_comment(comment)
        ):
            # Comments on an optional parens wrapping a single leaf should belong to
            # the wrapped node except if it's a type comment. Pinning the comment like
            # this avoids unstable formatting caused by comment migration.
            if len(self.leaves) < 2:
                comment.type = STANDALONE_COMMENT
                comment.prefix = ""
                return False

            last_leaf = self.leaves[-2]
        self.comments.setdefault(id(last_leaf), []).append(comment)
        return True

    def comments_after(self, leaf: Leaf) -> List[Leaf]:
        """Generate comments that should appear directly after `leaf`."""
        return self.comments.get(id(leaf), [])

    def remove_trailing_comma(self) -> None:
        """Remove the trailing comma and moves the comments attached to it."""
        trailing_comma = self.leaves.pop()
        trailing_comma_comments = self.comments.pop(id(trailing_comma), [])
        self.comments.setdefault(id(self.leaves[-1]), []).extend(
            trailing_comma_comments
        )

    def is_complex_subscript(self, leaf: Leaf) -> bool:
        """Return True iff `leaf` is part of a slice with non-trivial exprs."""
        open_lsqb = self.bracket_tracker.get_open_lsqb()
        if open_lsqb is None:
            return False

        subscript_start = open_lsqb.next_sibling

        if isinstance(subscript_start, Node):
            if subscript_start.type == syms.listmaker:
                return False

            if subscript_start.type == syms.subscriptlist:
                subscript_start = child_towards(subscript_start, leaf)
        return subscript_start is not None and any(
            n.type in TEST_DESCENDANTS for n in subscript_start.pre_order()
        )

    def enumerate_with_length(
        self, reversed: bool = False
    ) -> Iterator[Tuple[Index, Leaf, int]]:
        """Return an enumeration of leaves with their length.

        Stops prematurely on multiline strings and standalone comments.
        """
        op = cast(
            Callable[[Sequence[Leaf]], Iterator[Tuple[Index, Leaf]]],
            enumerate_reversed if reversed else enumerate,
        )
        for index, leaf in op(self.leaves):
            length = len(leaf.prefix) + len(leaf.value)
            if "\n" in leaf.value:
                return  # Multiline strings, we can't continue.

            for comment in self.comments_after(leaf):
                length += len(comment.value)

            yield index, leaf, length

    def clone(self) -> "Line":
        return Line(
            mode=self.mode,
            depth=self.depth,
            inside_brackets=self.inside_brackets,
            should_split_rhs=self.should_split_rhs,
            magic_trailing_comma=self.magic_trailing_comma,
        )

    def __str__(self) -> str:
        """Render the line."""
        if not self:
            return "\n"

        indent = "    " * self.depth
        leaves = iter(self.leaves)
        first = next(leaves)
        res = f"{first.prefix}{indent}{first.value}"
        for leaf in leaves:
            res += str(leaf)
        for comment in itertools.chain.from_iterable(self.comments.values()):
            res += str(comment)

        return res + "\n"

    def __bool__(self) -> bool:
        """Return True if the line has leaves or comments."""
        return bool(self.leaves or self.comments)


class LineGenerator(Visitor[Line]):
    """redefine to:
        1. remove formatting functionality
        2. utilise redefined Line class

    Generates reformatted Line objects.  Empty lines are not emitted.

    Note: destroys the tree it's visiting by mutating prefixes of its leaves
    in ways that will no longer stringify to valid Python code on the tree.
    """

    def __init__(self, mode: Mode) -> None:
        self.mode = mode
        self.current_line: Line
        self.__post_init__()

    def line(self, indent: int = 0) -> Iterator[Line]:
        """Generate a line.

        If the line is empty, only emit if it makes sense.
        If the line is too long, split it first and then generate.

        If any lines were generated, set up a new current_line.
        """
        if not self.current_line:
            self.current_line.depth += indent
            return  # Line is empty, don't emit. Creating a new one unnecessary.

        complete_line = self.current_line
        self.current_line = Line(mode=self.mode, depth=complete_line.depth + indent)
        yield complete_line

    def visit_default(self, node: LN) -> Iterator[Line]:
        """Default `visit_*()` implementation. Recurses to children of `node`."""
        if isinstance(node, Leaf):
            any_open_brackets = self.current_line.bracket_tracker.any_open_brackets()
            for comment in generate_comments(node, preview=self.mode.preview):
                if any_open_brackets:
                    # any comment within brackets is subject to splitting
                    self.current_line.append(comment)
                elif comment.type == token.COMMENT:
                    # regular trailing comment
                    self.current_line.append(comment)
                    yield from self.line()

                else:
                    # regular standalone comment
                    yield from self.line()

                    self.current_line.append(comment)
                    yield from self.line()

            normalize_prefix(node, inside_brackets=any_open_brackets)
            # if self.mode.string_normalization and node.type == token.STRING:
            #     node.value = normalize_string_prefix(node.value)
            #     node.value = normalize_string_quotes(node.value)
            # if node.type == token.NUMBER:
            #     normalize_numeric_literal(node)
            if node.type not in WHITESPACE:
                self.current_line.append(node)
        yield from super().visit_default(node)

    def visit_INDENT(self, node: Leaf) -> Iterator[Line]:
        """Increase indentation level, maybe yield a line."""
        # In blib2to3 INDENT never holds comments.
        yield from self.line(+1)
        yield from self.visit_default(node)

    def visit_DEDENT(self, node: Leaf) -> Iterator[Line]:
        """Decrease indentation level, maybe yield a line."""
        # The current line might still wait for trailing comments.  At DEDENT time
        # there won't be any (they would be prefixes on the preceding NEWLINE).
        # Emit the line then.
        yield from self.line()

        # While DEDENT has no value, its prefix may contain standalone comments
        # that belong to the current indentation level.  Get 'em.
        yield from self.visit_default(node)

        # Finally, emit the dedent.
        yield from self.line(-1)

    def visit_stmt(
        self, node: Node, keywords: Set[str], parens: Set[str]
    ) -> Iterator[Line]:
        """Visit a statement.

        This implementation is shared for `if`, `while`, `for`, `try`, `except`,
        `def`, `with`, `class`, `assert`, and assignments.

        The relevant Python language `keywords` for a given statement will be
        NAME leaves within it. This methods puts those on a separate line.

        `parens` holds a set of string leaf values immediately after which
        invisible parens should be put.
        """
        # normalize_invisible_parens(node, parens_after=parens, preview=self.mode.preview)
        for child in node.children:
            if is_name_token(child) and child.value in keywords:
                yield from self.line()

            yield from self.visit(child)

    def visit_funcdef(self, node: Node) -> Iterator[Line]:
        """Visit function definition."""
        if Preview.annotation_parens not in self.mode:
            yield from self.visit_stmt(node, keywords={"def"}, parens=set())
        else:
            yield from self.line()

            # Remove redundant brackets around return type annotation.
            # is_return_annotation = False
            # for child in node.children:
            #     if child.type == token.RARROW:
            #         is_return_annotation = True
            #     elif is_return_annotation:
            #         if child.type == syms.atom and child.children[0].type == token.LPAR:
            #             if maybe_make_parens_invisible_in_atom(
            #                 child,
            #                 parent=node,
            #                 remove_brackets_around_comma=False,
            #             ):
            #                 wrap_in_parentheses(node, child, visible=False)
            #         else:
            #             wrap_in_parentheses(node, child, visible=False)
            #         is_return_annotation = False

            for child in node.children:
                yield from self.visit(child)

    def visit_match_case(self, node: Node) -> Iterator[Line]:
        """Visit either a match or case statement."""
        # normalize_invisible_parens(node, parens_after=set(), preview=self.mode.preview)

        yield from self.line()
        for child in node.children:
            yield from self.visit(child)

    def visit_suite(self, node: Node) -> Iterator[Line]:
        """Visit a suite."""
        if self.mode.is_pyi and is_stub_suite(node):
            yield from self.visit(node.children[2])
        else:
            yield from self.visit_default(node)

    def visit_simple_stmt(self, node: Node) -> Iterator[Line]:
        """Visit a statement without nested statements."""
        # prev_type: Optional[int] = None
        # for child in node.children:
        #     if (prev_type is None or prev_type == token.SEMI) and is_arith_like(child):
        #         wrap_in_parentheses(node, child, visible=False)
        #     prev_type = child.type

        is_suite_like = node.parent and node.parent.type in STATEMENT
        if is_suite_like:
            if self.mode.is_pyi and is_stub_body(node):
                yield from self.visit_default(node)
            else:
                yield from self.line(+1)
                yield from self.visit_default(node)
                yield from self.line(-1)

        else:
            if (
                not self.mode.is_pyi
                or not node.parent
                or not is_stub_suite(node.parent)
            ):
                yield from self.line()
            yield from self.visit_default(node)

    def visit_async_stmt(self, node: Node) -> Iterator[Line]:
        """Visit `async def`, `async for`, `async with`."""
        yield from self.line()

        children = iter(node.children)
        for child in children:
            yield from self.visit(child)

            if child.type == token.ASYNC:
                break

        internal_stmt = next(children)
        for child in internal_stmt.children:
            yield from self.visit(child)

    def visit_decorators(self, node: Node) -> Iterator[Line]:
        """Visit decorators."""
        for child in node.children:
            yield from self.line()
            yield from self.visit(child)

    def visit_power(self, node: Node) -> Iterator[Line]:
        # for idx, leaf in enumerate(node.children[:-1]):
        #     next_leaf = node.children[idx + 1]
        #
        #     if not isinstance(leaf, Leaf):
        #         continue
        #
        #     value = leaf.value.lower()
        #     if (
        #         leaf.type == token.NUMBER
        #         and next_leaf.type == syms.trailer
        #         # Ensure that we are in an attribute trailer
        #         and next_leaf.children[0].type == token.DOT
        #         # It shouldn't wrap hexadecimal, binary and octal literals
        #         and not value.startswith(("0x", "0b", "0o"))
        #         # It shouldn't wrap complex literals
        #         and "j" not in value
        #     ):
        #         wrap_in_parentheses(node, leaf)

        # if Preview.remove_redundant_parens in self.mode:
        #     remove_await_parens(node)
        yield from self.visit_default(node)

    def visit_SEMI(self, leaf: Leaf) -> Iterator[Line]:
        """Remove a semicolon and put the other statement on a separate line."""
        yield from self.line()

    def visit_ENDMARKER(self, leaf: Leaf) -> Iterator[Line]:
        """End of file. Process outstanding comments and end with a newline."""
        yield from self.visit_default(leaf)
        yield from self.line()

    def visit_STANDALONE_COMMENT(self, leaf: Leaf) -> Iterator[Line]:
        if not self.current_line.bracket_tracker.any_open_brackets():
            yield from self.line()
        yield from self.visit_default(leaf)

    def visit_factor(self, node: Node) -> Iterator[Line]:
        """Force parentheses between a unary op and a binary power:

        -2 ** 8 -> -(2 ** 8)
        """
        _operator, operand = node.children
        if (
            operand.type == syms.power
            and len(operand.children) == 3
            and operand.children[1].type == token.DOUBLESTAR
        ):
            lpar = Leaf(token.LPAR, "(")
            rpar = Leaf(token.RPAR, ")")
            index = operand.remove() or 0
            node.insert_child(index, Node(syms.atom, [lpar, operand, rpar]))
        yield from self.visit_default(node)

    def visit_STRING(self, leaf: Leaf) -> Iterator[Line]:
        # if is_docstring(leaf) and "\\\n" not in leaf.value:
        #     # We're ignoring docstrings with backslash newline escapes because changing
        #     # indentation of those changes the AST representation of the code.
        #     docstring = leaf.value  # normalize_string_prefix(leaf.value)
        #     prefix = get_string_prefix(docstring)
        #     docstring = docstring[len(prefix) :]  # Remove the prefix
        #     quote_char = docstring[0]
        #     # A natural way to remove the outer quotes is to do:
        #     #   docstring = docstring.strip(quote_char)
        #     # but that breaks on """""x""" (which is '""x').
        #     # So we actually need to remove the first character and the next two
        #     # characters but only if they are the same as the first.
        #     quote_len = 1 if docstring[1] != quote_char else 3
        #     docstring = docstring[quote_len:-quote_len]
        #     docstring_started_empty = not docstring
        #     indent = " " * 4 * self.current_line.depth
        #
        #     if is_multiline_string(leaf):
        #         docstring = fix_docstring(docstring, indent)
        #     else:
        #         docstring = docstring.strip()
        #
        #     if docstring:
        #         # Add some padding if the docstring starts / ends with a quote mark.
        #         if docstring[0] == quote_char:
        #             docstring = " " + docstring
        #         if docstring[-1] == quote_char:
        #             docstring += " "
        #         if docstring[-1] == "\\":
        #             backslash_count = len(docstring) - len(docstring.rstrip("\\"))
        #             if backslash_count % 2:
        #                 # Odd number of tailing backslashes, add some padding to
        #                 # avoid escaping the closing string quote.
        #                 docstring += " "
        #     elif not docstring_started_empty:
        #         docstring = " "
        #
        #     # We could enforce triple quotes at this point.
        #     quote = quote_char * quote_len
        #
        #     if Preview.long_docstring_quotes_on_newline in self.mode:
        #         # We need to find the length of the last line of the docstring
        #         # to find if we can add the closing quotes to the line without
        #         # exceeding the maximum line length.
        #         # If docstring is one line, then we need to add the length
        #         # of the indent, prefix, and starting quotes. Ending quote are
        #         # handled later
        #         lines = docstring.splitlines()
        #         last_line_length = len(lines[-1]) if docstring else 0
        #
        #         if len(lines) == 1:
        #             last_line_length += len(indent) + len(prefix) + quote_len
        #
        #         # If adding closing quotes would cause the last line to exceed
        #         # the maximum line length then put a line break before the
        #         # closing quotes
        #         if last_line_length + quote_len > self.mode.line_length:
        #             leaf.value = prefix + quote + docstring + "\n" + indent + quote
        #         else:
        #             leaf.value = prefix + quote + docstring + quote
        #     else:
        #         leaf.value = prefix + quote + docstring + quote

        yield from self.visit_default(leaf)

    def __post_init__(self) -> None:
        """You are in a twisty little maze of passages."""
        self.current_line = Line(mode=self.mode)

        v = self.visit_stmt
        Ø: Set[str] = set()
        self.visit_assert_stmt = partial(v, keywords={"assert"}, parens={"assert", ","})
        self.visit_if_stmt = partial(
            v, keywords={"if", "else", "elif"}, parens={"if", "elif"}
        )
        self.visit_while_stmt = partial(v, keywords={"while", "else"}, parens={"while"})
        self.visit_for_stmt = partial(v, keywords={"for", "else"}, parens={"for", "in"})
        self.visit_try_stmt = partial(
            v, keywords={"try", "except", "else", "finally"}, parens=Ø
        )
        if self.mode.preview:
            self.visit_except_clause = partial(
                v, keywords={"except"}, parens={"except"}
            )
            self.visit_with_stmt = partial(v, keywords={"with"}, parens={"with"})
        else:
            self.visit_except_clause = partial(v, keywords={"except"}, parens=Ø)
            self.visit_with_stmt = partial(v, keywords={"with"}, parens=Ø)
        self.visit_classdef = partial(v, keywords={"class"}, parens=Ø)
        self.visit_expr_stmt = partial(v, keywords=Ø, parens=ASSIGNMENTS)
        self.visit_return_stmt = partial(v, keywords={"return"}, parens={"return"})
        self.visit_import_from = partial(v, keywords=Ø, parens={"import"})
        self.visit_del_stmt = partial(v, keywords=Ø, parens={"del"})
        self.visit_async_funcdef = self.visit_async_stmt
        self.visit_decorated = self.visit_decorators

        # PEP 634
        self.visit_match_stmt = self.visit_match_case
        self.visit_case_block = self.visit_match_case
