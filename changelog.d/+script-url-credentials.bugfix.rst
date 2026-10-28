``pipx run`` and ``pipx install`` now refuse an ``http`` or ``https`` script URL with credentials, naming it with the
password masked. Before, a URL such as ``https://user:password@host/tool.py`` failed with an error that printed the
password in clear text and wrote it to the log. ``pipx install`` also reports a malformed script URL as an error instead
of a traceback.
