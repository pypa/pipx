## Running a specific version of a package

The `PACKAGE` argument is a
[requirement specifier](https://packaging.python.org/en/latest/glossary/#term-Requirement-Specifier), so you can pin
versions, ranges, or extras:

```
pipx run mpremote==1.20.0
pipx run --spec esptool==4.6.2 esptool.py
pipx run --spec 'esptool>=4.5' esptool.py
```

Requirement specifiers containing `>`, `<`, or spaces need quoting.

## Running with extra dependencies

`--with` adds packages to the temporary environment alongside the main app:

```
pipx run --with requests --with rich my-script.py
```

## Running from source control

`pipx run` accepts git URLs through `--spec`. Using `black` as an example:

```
pipx run --spec git+https://github.com/psf/black.git black
pipx run --spec git+ssh://git@github.com/psf/black black
pipx run --spec git+https://github.com/psf/black.git@branch black
pipx run --spec git+https://github.com/psf/black.git@ce14fa8b497bae2b50ec48b3bd7022573a59cdb1 black
pipx run --spec https://github.com/psf/black/archive/18.9b0.zip black
```

## Running from URL

You can run `.py` files hosted anywhere:

```
pipx run https://gist.githubusercontent.com/cs01/fa721a17a326e551ede048c5088f9e0f/raw/6bdfbb6e9c1132b1c38fdd2f195d4a24c540c324/pipx-demo.py
```

## Running scripts with dependencies (PEP 723)

Scripts can declare their own dependencies using
[inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/). pipx reads the
`# /// script` block and installs the listed packages before running:

```python
# test.py

# /// script
# dependencies = ["requests"]
# ///

import sys
import requests
project = sys.argv[1]
data = requests.get(f"https://pypi.org/pypi/{project}/json").json()
print(data["info"]["version"])
```

```
> pipx run test.py pipx
1.9.0
```

pipx creates a cached virtual environment keyed to the script's dependency list. Changing the dependencies creates a
fresh environment.
