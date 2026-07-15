Record the interpreter and backend in the structured `install`, `upgrade`, and `upgrade-all` results, list
`PIPX_GLOBAL_COMPLETION_DIR` in `pipx environment`, and show the shell-completion directory in `pipx list`. Completions
had a global override that pipx honoured but never surfaced, and the records omitted which Python and backend produced a
venv.
