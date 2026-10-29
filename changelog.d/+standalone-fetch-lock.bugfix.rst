Stop two pipx commands that fetch the same standalone Python at once from leaving an interpreter with part of its
standard library missing in ``PIPX_HOME/py``. Both staged the build in one fixed directory and each deleted the other's
half-copied tree as a leftover; pipx now holds a per-version lock while it fetches, so the second command waits and
reuses the first one's build. ``pipx interpreter list``, ``prune`` and ``upgrade`` also skip the staging and backup
directories of a fetch in progress instead of treating them as interpreters. An interpreter that an earlier fetch
already left incomplete still needs deleting by hand.
