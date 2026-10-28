``pipx install-all --backend uv`` now translates index options that a pip recording spells as an abbreviation pip
accepts, such as ``--index-u URL``, instead of dropping them and installing from the default index. A recorded pip
``--index URL`` now becomes uv ``--default-index URL``, matching how pip read it.
