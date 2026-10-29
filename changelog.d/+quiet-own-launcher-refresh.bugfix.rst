Where pipx copies launchers instead of linking them, as on Windows without symlink rights, ``pipx reinstall`` and
``pipx install --force`` no longer warn ``Overwriting file`` for the package's own launcher. Windows ``.exe`` launchers
embed their build time, so a rebuilt one never matched its old copy byte for byte and every reinstall warned. pipx now
recognises its own copy by the interpreter it names and replaces it without a warning; a file another venv or the user
put there still gets one.
