A ``pipx run`` that names an app the package does not provide, such as ``pipx run --spec black blackk``, no longer
expires the cached environment, so the corrected command reuses it instead of rebuilding. A failed venv creation or
install still expires the entry.
