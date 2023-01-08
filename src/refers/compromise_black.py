"""sorry black, you've been compromised"""
from functools import partial
from typing import (
    Iterator,
    TypeVar,
)
from typing import Set

from black.comments import generate_comments
from black.mode import Mode, Preview
from black.nodes import ASSIGNMENTS
from black.nodes import Visitor
from black.nodes import WHITESPACE, STATEMENT
from black.nodes import is_name_token
from black.nodes import is_stub_suite, is_stub_body
from black.nodes import syms

# types
T = TypeVar("T")
Index = int
LeafID = int


from blib2to3.pgen2 import token

from typing import (
    Union,
)

from blib2to3.pytree import Node, Leaf  # type: ignore
from black.linegen import normalize_prefix, Line

LN = Union[Leaf, Node]


class LineGenerator(Visitor[Line]):
    """redefine to:
        1. limit formatting functionality as much as possible
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
