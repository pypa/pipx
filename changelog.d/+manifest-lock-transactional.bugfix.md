Apply `pipx manifest lock` as all-or-nothing. When a manifest declares locks for several tools, pipx wrote the
regenerated files one at a time, so a failure partway left some locks new and others old. Each target is now backed up
before it is replaced and every applied lock is rolled back if any replacement fails.
