Stop ``pipx interpreter upgrade`` from moving an environment to another Python found on ``PATH`` when the newest release
of its package has a ``Requires-Python`` that rules out the new standalone build. The command reported the patch
upgrade as done while the environment now ran on, for example, ``/usr/bin/python3.11``. It now fails, restores the
environment on its standalone build, and exits 1.
