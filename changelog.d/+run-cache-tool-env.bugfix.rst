``pipx run`` no longer reuses a cached environment after a change to a variable outside ``PIP_*`` and ``UV_*`` that
decides which config file pip or uv reads, which proxy or index answers, which certificate is trusted or which
credentials are sent, such as ``XDG_CONFIG_HOME``, ``SSL_CERT_FILE``, ``HTTPS_PROXY`` or ``NETRC``. The values only
feed the cache key's hash, so secrets in them stay out of cache paths and logs.
