Let an environment take over an app, manual page, or completion name whose link points to a file that another installed
environment no longer ships. pipx before 1.18.0 left such links behind when an upgrade dropped an app, and pipx kept
them as collisions that only ``--force`` cleared. A link counts as left over when the environment it points into no
longer lists the file in its metadata. The collision warning for a link whose target is missing now says so.
