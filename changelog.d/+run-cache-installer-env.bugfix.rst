``pipx run`` now includes the installer's environment variables (``PIP_*``, or ``UV_*`` under the uv backend) in its
cache key. A run after changing ``PIP_INDEX_URL``, ``PIP_FIND_LINKS`` or ``UV_INDEX_URL`` reused the environment built
from the previous index for up to 14 days.
