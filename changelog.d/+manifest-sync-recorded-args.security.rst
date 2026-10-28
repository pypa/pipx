``pipx manifest sync`` now keeps the installer and venv options recorded for an environment that already exists, such
as ``--index-url``. It used to reinstall the tool from the default index and erase the recorded options.
