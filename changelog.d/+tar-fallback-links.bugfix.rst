Keep standalone Python archive members inside the unpack directory on Python 3.11.0 to 3.11.3, which lack
``tarfile.data_filter``. pipx's own extractor checked member names as text, so a member whose path went through a
symlink unpacked earlier from the same archive was written wherever that link led. It now resolves each path through
the links already on disk, extracts under normalized names like the data filter does, and refuses a hard link to a
symlink.
