Keep pipx's ``pipx_metadata.json`` when the installer replaces it with a wheel's data file of the same name. A failed
``pipx install --force``, ``pipx upgrade`` or ``pipx inject``, or a ``pipx runpip APP install`` of a dependency, used to
leave the wheel's copy in place, and later commands read its index arguments, spec and suffix as pipx's own. pipx now
puts its record back after every installer run.
