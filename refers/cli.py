import argparse

from refers.refers import format_doc


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rootdir", type=str, default=None)
    parser.add_argument("--allow_not_found_tags", action="store_true", default=None)
    parser.add_argument("--accepted_tag_extensions", type=str, nargs="+", default=None)
    parser.add_argument("--accepted_ref_extensions", type=str, nargs="+", default=None)
    parser.add_argument("--dirs2ignore", type=str, nargs="+", default=None)
    parser.add_argument("--dirs2search", type=str, nargs="+", default=None)
    parser.add_argument("--tag_files", type=str, nargs="+", default=None)
    parser.add_argument("--ref_files", type=str, nargs="+", default=None)
    args = parser.parse_args()
    format_doc(
        rootdir=args.rootdir,
        allow_not_found_tags=args.allow_not_found_tags,
        accepted_tag_extensions=args.accepted_tag_extensions,
        accepted_ref_extensions=args.accepted_ref_extensions,
        dirs2ignore=args.dirs2ignore,
        dirs2search=args.dirs2search,
        tag_files=args.tag_files,
        ref_files=args.ref_files,
    )
