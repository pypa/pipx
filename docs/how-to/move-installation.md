## Moving your pipx installation

The below code snippets show how to move your pipx installation to a new directory. As an example, they move from a
non-default location to the current default locations. If you wish to move to a different location, just replace the
`NEW_LOCATION` value.

### MacOS

Current default location: `~/.local`

```bash
NEW_LOCATION=~/.local
cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
logs_dir=$(pipx environment --value PIPX_LOG_DIR)
trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
home_dir=$(pipx environment --value PIPX_HOME)
rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
mkdir -p $NEW_LOCATION && mv "$home_dir" $NEW_LOCATION
pipx reinstall-all
```

### Linux

Current default location: `~/.local/share`

```bash
cache_dir=$(pipx environment --value PIPX_VENV_CACHEDIR)
logs_dir=$(pipx environment --value PIPX_LOG_DIR)
trash_dir=$(pipx environment --value PIPX_TRASH_DIR)
home_dir=$(pipx environment --value PIPX_HOME)
# If you wish another location, replace the expression below
# and set `NEW_LOCATION` explicitly
NEW_LOCATION="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$cache_dir" "$logs_dir" "$trash_dir"
mkdir -p $NEW_LOCATION && mv "$home_dir" $NEW_LOCATION
pipx reinstall-all
```

### Windows

Current default location: `~/pipx`

```powershell
$NEW_LOCATION = Join-Path "$HOME" 'pipx'
$cache_dir = pipx environment --value PIPX_VENV_CACHEDIR
$logs_dir = pipx environment --value PIPX_LOG_DIR
$trash_dir = pipx environment --value PIPX_TRASH_DIR
$home_dir = pipx environment --value PIPX_HOME

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$cache_dir", "$logs_dir", "$trash_dir"

# Remove the destination directory to ensure rename behavior of `Move-Item`
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$NEW_LOCATION"

Move-Item -Path $home_dir -Destination "$NEW_LOCATION"
pipx reinstall-all
```

If you would prefer doing it in bash via git-bash/WSL, feel free to use the MacOS/Linux instructions, changing the
`$NEW_LOCATION` to the Windows version.
