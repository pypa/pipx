# Valid package specifiers for pipx:
#   git+<URL>
#   <URL>
#   <pypi_package_name>
#   <pypi_package_name><version_specifier>


def abs_path_if_local(package_or_url: str, venv: Venv, pip_args: List[str]) -> str:
    """Return the absolute path if package_or_url represents a filepath
    and not a pypi package
    """
    # if valid url leave it untouched
    if urllib.parse.urlparse(package_or_url).scheme:
        return package_or_url

    pkg_path = Path(package_or_url)
    if not pkg_path.exists():
        # no existing path, must be pypi package or non-existent
        return package_or_url

    # Editable packages are either local or url, non-url must be local.
    # https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs
    if "--editable" in pip_args and pkg_path.exists():
        return str(pkg_path.resolve())

    if not valid_pypi_name(package_or_url):
        return str(pkg_path.resolve())

    # If all of the above conditions do not return, we may have used a pypi
    #   package.
    # If we find a pypi package with this name installed, assume we just
    #   installed it.
    pip_search_args: List[str]

    # If user-defined pypi index url, then use it for search
    try:
        arg_i = pip_args.index("--index-url")
    except ValueError:
        pip_search_args = []
    else:
        pip_search_args = pip_args[arg_i : arg_i + 2]

    pip_search_result_str = venv.pip_search(package_or_url, pip_search_args)
    pip_search_results = pip_search_result_str.split("\n")

    # Get package_or_url and following related lines from pip search stdout
    pkg_found = False
    pip_search_found = []
    for pip_search_line in pip_search_results:
        if pkg_found:
            if re.search(r"^\s", pip_search_line):
                pip_search_found.append(pip_search_line)
            else:
                break
        elif pip_search_line.startswith(package_or_url):
            pip_search_found.append(pip_search_line)
            pkg_found = True
    pip_found_str = " ".join(pip_search_found)

    if pip_found_str.startswith(package_or_url) and "INSTALLED" in pip_found_str:
        return package_or_url
    else:
        return str(pkg_path.resolve())
