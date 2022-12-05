TAG_COMMENT_ID = "@tag:"
REF_COMMENT_ID = "@ref:"
CODE_RE_TAG = rf"{TAG_COMMENT_ID}(\w*)"  # regex of tag in code
DOC_REGEX_TAG = rf"{REF_COMMENT_ID}(\w*)(:\w+)?"  # regex of tag in document
DOC_OUT_ID = "_refers"
UNKNOWN_ID = "TAG-NOT-FOUND"
LIBRARY_NAME = "refers"
COMMENT_SYMBOL = {
    ".py": "#",
    ".jl": "#",
    ".c": "//",
    ".cpp": "//",
    ".cs": "//",
    ".java": "//",
    ".js": "//",
    ".go": "//",
    ".html": "<! --",
    ".sh": "#",
    ".ruby": "#",
    ".csh": "#",
    ".xml": "///",
    ".tex": "%",
    ".m": "%",
}
