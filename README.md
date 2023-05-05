# refers
*<p style="text-align: center;">reference code simply</p>*
![Tests](https://github.com/Stoops-ML/refers/actions/workflows/test.yml/badge.svg)

The refers library allows referencing plain text files from plain text files.

Usage:
1. Add a `@tag` to the line that you want to reference: `@tag:TAG_NAME`
2. To reference the tag use `@ref` followed by an *optional* option: `@ref:TAG_NAME:OPTION`
3. run the refers library in the command line


The refers library will create new files with the outputted references in place of the tags.
Changes of line placement, file name, relative path etc. are reflected in the updated references when the refers library is executed.

## Reference options

| `ref` option  | result                               |
|---------------|--------------------------------------|
| *blank*       | file name and line number            |
| :file         | file name                            |
| :line         | line number                          |
| :link         | relative link to file                |
| :linkline     | relative link to line in file        |
| :fulllink     | full path link to file               |
| :fulllinkline | full path link to line in file       |
| :quote        | quote line                           |
| :quotecode    | quote line of code without comment   |
| :func         | get function name that contains line |
| :class        | get class name that contains line    |

Relative paths are given from the directory containing the pyproject.toml.

## Future Work
Currently line continuation of code is only supported in python (using [`black`](https://github.com/psf/black)).
Future work will include supporting line continuation for all languages.
