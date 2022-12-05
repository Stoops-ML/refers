![Tests](https://github.com/Stoops-ML/refers/actions/workflows/tests.yml/badge.svg)
# refers
*<p style="text-align: center;">reference code simply</p>*
The refers library allows referencing plain text files from plain text files. To reference code from a file:
1. Add a tag to the line that you want to reference: `@tag:TAG_NAME`
2. Add a reference to the tag followed by an option: `@ref:TAG_NAME:OPTION`
3. run the refers library in the command line


The refers library will create new files with the outputted references in place of the tags. 
Changes of line placement, file name, relative path etc. are reflected in the updated references when the refers library is executed.

## Reference options

| `ref` option  | result                                            |
|---------------|---------------------------------------------------|
| *blank*       | file name and line number                         |
| :file         | file name                                         |
| :line         | line number                                       |
| :link         | relative link to file                             |
| :linkline     | relative link to line in file                     |
| :fulllink     | full path link to file                            |
| :fulllinkline | full path link to line in file                    |
| :p            | print relative path from one parent up            |
| :pp           | print relative path from number of `p` parents up |
| :quote        | quote line                                        |
| :quotecode    | quote line of code without comment                |

Relative paths are given from the directory containing the pyproject.toml.
