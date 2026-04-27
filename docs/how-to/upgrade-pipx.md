## Upgrade pipx

On macOS:

```
brew update && brew upgrade pipx
```

On Ubuntu Linux:

```
sudo apt upgrade pipx
```

On Fedora Linux:

```
sudo dnf update pipx
```

On Windows:

```
scoop update pipx
```

Otherwise, upgrade via pip:

```
python3 -m pip install --user -U pipx
```

### Note: Upgrading pipx from a pre-0.15.0.0 version to 0.15.0.0 or later

After upgrading to pipx 0.15.0.0 or above from a pre-0.15.0.0 version, you must re-install all packages to take
advantage of the new persistent pipx metadata files introduced in the 0.15.0.0 release. These metadata files store pip
specification values, injected packages, any custom pip arguments, and more in each main package's venv.

If you have no packages installed using the `--spec` option, and no venvs with injected packages, you can do this by
running `pipx reinstall-all`.

If you have any packages installed using the `--spec` option or venvs with injected packages, you should reinstall
packages manually using `pipx uninstall-all`, followed by `pipx install` and possibly `pipx inject`.
