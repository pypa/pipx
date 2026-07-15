Apply a 30-second timeout and a 10 MiB size limit when downloading a remote `pipx run` or `pipx install` script, so a
stalled or oversized URL can no longer hang pipx or exhaust memory. `pipx run` also accepts a script URL with a query
string, such as `tool.py?raw=1`, by matching on the URL path.
