On Windows under the uv backend, ``pipx run script.py`` now releases the run-cache lock before the script starts. pipx
held it until the script exited, so a second run of the same script waited without a message, and a script that ran
itself through pipx never finished.
