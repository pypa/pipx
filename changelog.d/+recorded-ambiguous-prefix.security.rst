pipx no longer records an abbreviation of a one-shot pip option that the current pip finds ambiguous but an older pip
accepts, such as ``--requirem FILE``, which pip 24.0 reads as ``--requirement FILE``. With such a shared pip, a later
``pipx upgrade`` or ``pipx reinstall`` used to replay it and install from whatever another account had put at that path.
An existing record drops it when read, and an abbreviation that could name a source option such as ``--constraint``
goes through the same replay check as that option.
