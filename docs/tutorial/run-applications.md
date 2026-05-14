## Running an Application in a Temporary Virtual Environment

`pipx run` downloads and runs Python applications in a one-time, temporary environment, then leaves your system
untouched. Use it to initialize a new project, check an app's help text, or try a tool without committing to an install.

The blog post [How to set up a perfect Python project](https://sourcery.ai/blog/python-best-practices/) uses `pipx run`
to kickstart a new project with [cookiecutter](https://github.com/cookiecutter/cookiecutter).

```
pipx run APP [ARGS...]
```

pipx installs the package in an isolated, temporary directory and invokes the app:

```
> pipx run pycowsay moo

  ---
< moo >
  ---
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||


```

Arguments after the application name pass straight through:

```
> pipx run pycowsay these arguments are all passed to pycowsay!

  -------------------------------------------
< these arguments are all passed to pycowsay! >
  -------------------------------------------
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||

```

pipx caches virtual environments per app for a few days. After they expire, pipx fetches the latest version.

### Ambiguous arguments

pipx can consume arguments meant for the application:

```
> pipx run pycowsay --py

usage: pipx run [-h] [--no-cache] [--pypackages] [--spec SPEC] [--verbose] [--python PYTHON]
                [--system-site-packages] [--index-url INDEX_URL] [--editable] [--pip-args PIP_ARGS]
                app ...
pipx run: error: ambiguous option: --py could match --pypackages, --python
```

Place `--` before the app name to forward all arguments verbatim:

```
> pipx run -- pycowsay --py


  ----
< --py >
  ----
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||


```

### App name differs from package name

Use `--spec` to specify the package and provide the app name separately:

```
pipx run --spec PACKAGE APP
```

The [esptool](https://github.com/espressif/esptool) package, for example, exposes executables with different names:

```
>> pipx run esptool
'esptool' executable script not found in package 'esptool'.
Available executable scripts:
    esp_rfc2217_server.py - usage: 'pipx run --spec esptool esp_rfc2217_server.py [arguments?]'
    espefuse.py - usage: 'pipx run --spec esptool espefuse.py [arguments?]'
    espsecure.py - usage: 'pipx run --spec esptool espsecure.py [arguments?]'
    esptool.py - usage: 'pipx run --spec esptool esptool.py [arguments?]'
```

Run them with `--spec`:

```
pipx run --spec esptool esptool.py
```

The `.py` is part of the executable name as declared by the package. The
[pymodbus](https://github.com/pymodbus-dev/pymodbus) package shows a similar pattern:

```
pipx run --spec pymodbus[repl] pymodbus.console
pipx run --spec pymodbus[repl] pymodbus.server
pipx run --spec pymodbus[repl] pymodbus.simulator
```

Package authors can avoid this `--spec` requirement by declaring a
[`pipx.run` entry point](../explanation/making-packages-compatible.md#the-pipxrun-entry-point-group) in their package
metadata.
