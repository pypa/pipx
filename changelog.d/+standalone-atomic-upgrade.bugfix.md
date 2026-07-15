Make a standalone Python upgrade atomic. pipx used to delete the existing interpreter before downloading its
replacement, so a failed download or unpack left no interpreter at all. The new build is now staged beside the old one
and swapped in only once it is complete, and a failed swap restores the previous build.
