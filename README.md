# extract_attachments
Extract attachments from maildir(s) using regex patterns:

```
usage: extract_attachments.py [-h] [-n] [-p PATTERN] [-d DIRECTORY] [-v]
                              target_dirs [target_dirs ...]

positional arguments:
  target_dirs

optional arguments:
  -h, --help            show this help message and exit
  -n, --dry-run         perform a trial run with no changes made
  -p PATTERN, --pattern PATTERN
                        regex pattern that filename must match
  -d DIRECTORY, --directory DIRECTORY
                        where to save attachments
  -v, --verbose         show verbose output
```
