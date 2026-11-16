``--fetch-python`` now resumes a standalone Python download when the connection drops before its ``Content-Length``.
Before, pipx stopped at the partial archive and failed with a checksum mismatch instead of resuming.
