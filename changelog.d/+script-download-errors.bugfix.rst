``pipx run`` now names the script URL, with credentials masked, when a download fails, as ``pipx install`` already did.
``pipx install`` of a script URL whose body does not decode in its declared charset, or declares an unknown one, now
reports an error instead of a traceback, as ``pipx run`` already did.
