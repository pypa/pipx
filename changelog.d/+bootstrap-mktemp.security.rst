Create the self-managed bootstrap environment in the installation guide with ``mktemp -d`` instead of the fixed
``/tmp/bootstrap`` path, which another local user could create first and plant code in that ran as the reader, and as
root at the ``sudo`` step.
