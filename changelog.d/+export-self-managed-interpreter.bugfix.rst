``pipx list --json`` no longer exports the interpreter a self-managed pipx recorded when that path no longer leads to
the interpreter its environment runs on, such as a removed bootstrap environment's ``python3``. ``pipx install-all``
then builds that environment on the default interpreter instead of whatever appears at the old path.
