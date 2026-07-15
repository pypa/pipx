Report `pipx expose` as a partial or failed operation when a resource cannot be linked because a foreign file already
occupies its target name. The command previously claimed success while silently leaving those apps or manual pages
unexposed; it now lists each conflict in the structured result and exits non-zero.
