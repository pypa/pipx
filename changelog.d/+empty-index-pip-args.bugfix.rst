Refuse an empty or whitespace-only index option inside ``--pip-args`` (``--index-url``, ``-i``, ``--extra-index-url``,
``--default-index``, ``--index``), and under the uv backend an empty index recorded by an earlier install, instead of
letting uv install from the default index.
