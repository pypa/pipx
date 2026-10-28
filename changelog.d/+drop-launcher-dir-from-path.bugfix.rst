Stop pipx from importing modules out of the directory of its own launcher script, or out of the working directory under
``python -m pipx``. After ``pip install --user pipx`` that directory is ``~/.local/bin``, where pipx links apps, so a
package shipping a script named ``json.py`` or ``shlex.py`` was imported by pipx in place of the standard library
module, and an exposed ``json.py`` broke every later pipx command, ``pipx uninstall`` included. Programs that import
``pipx.__main__`` no longer see their script directory on ``sys.path`` either.
