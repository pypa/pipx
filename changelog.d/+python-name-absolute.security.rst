Pass the absolute path ``PATH`` lookup found for ``--python python3.11`` on to the backend instead of the bare name. uv
read the bare name as a version request and could pick a ``.venv`` interpreter from a parent of the current directory.
A file in the current directory named like the value, such as ``./3.11``, no longer counts as a path either.
