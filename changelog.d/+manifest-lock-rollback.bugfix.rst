Restore every earlier lock when ``pipx manifest lock`` fails because a directory sits at a later tool's lock path.
pipx used to stop rolling back at that directory, keep the new locks of the tools before it, and delete their previous
versions.
