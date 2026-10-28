``pipx install`` with several packages no longer builds every environment on the Python it picked for one package whose
``Requires-Python`` rules out the default interpreter; the other packages keep the default Python.
