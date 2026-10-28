Restore the existing environment when ``pipx install --force`` or ``pipx install-all --force`` fails. A package whose
``Requires-Python`` made pipx rebuild on another interpreter left behind an empty environment without its app,
injected packages, or ``pipx_metadata.json`` when the rebuild failed, while pipx reported it had kept the environment.
Each forced install now copies the environment to pipx's trash first and puts it back on any failure.
