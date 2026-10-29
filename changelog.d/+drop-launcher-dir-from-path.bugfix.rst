Stop pipx from importing modules out of the directory of its own launcher script, or out of the working directory under
``python -m pipx``, once ``pipx.__main__`` starts. After ``pip install --user pipx`` that directory is ``~/.local/bin``,
where pipx links apps, so pipx imported a ``json.py`` or ``shlex.py`` script a package shipped there in place of the
standard library module, and an exposed ``json.py`` broke every later pipx command, ``pipx uninstall`` included. For
modules pip's launcher imports before that point, such as ``re`` and ``enum``, pipx refuses to expose apps named after
standard library modules. Programs that import ``pipx.__main__`` no longer see their script directory on ``sys.path``
either.
