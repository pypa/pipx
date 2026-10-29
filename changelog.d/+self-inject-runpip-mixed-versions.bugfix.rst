``pipx inject pipx`` without ``--include-apps`` and ``pipx runpip pipx`` on a pipx that manages itself no longer mix
old and new pipx code when they change the pipx package. Like ``pipx upgrade pipx``, they now load late imports from a
copy of the environment, which the next pipx command deletes from the trash.
