import sys
from pathlib import Path
from typing import Any, Dict

WIN = sys.platform.startswith("win")


def _exe_if_win(apps):
    return [f"{app}.exe" if WIN else app for app in apps]


# Versions of all packages possibly used in our tests
# Only apply _exe_if_win to entry_points, NOT scripts
PKG: Dict[str, Dict[str, Any]] = {
    "ansible": {
        "spec": "ansible==6.7.0",
        "apps": [
            "ansible",
            "ansible-config",
            "ansible-connection",
            "ansible-console",
            "ansible-doc",
            "ansible-galaxy",
            "ansible-inventory",
            "ansible-playbook",
            "ansible-pull",
            "ansible-test",
            "ansible-vault",
        ],
        "apps_of_dependencies": [],
    },
    "awscli": {
        "spec": "awscli==1.18.168",
        "apps": [
            "aws",
            "aws.cmd",
            "aws_bash_completer",
            "aws_completer",
            "aws_zsh_completer.sh",
        ],
        "apps_of_dependencies": _exe_if_win(
            [
                "pyrsa-decrypt",  # rsa EXE
                "pyrsa-encrypt",  # rsa EXE
                "pyrsa-keygen",  # rsa EXE
                "pyrsa-priv2pub",  # rsa EXE
                "pyrsa-sign",  # rsa EXE
                "pyrsa-verify",  # rsa EXE
            ]
        )
        + [
            "jp.py",  # jmespath.py NO_EXE
            "rst2html.py",  # docutils NO_EXE
            "rst2html4.py",  # docutils NO_EXE
            "rst2html5.py",  # docutils NO_EXE
            "rst2latex.py",  # docutils NO_EXE
            "rst2man.py",  # docutils NO_EXE
            "rst2odt.py",  # docutils NO_EXE
            "rst2odt_prepstyles.py",  # docutils NO_EXE
            "rst2pseudoxml.py",  # docutils NO_EXE
            "rst2s5.py",  # docutils NO_EXE
            "rst2xetex.py",  # docutils NO_EXE
            "rst2xml.py",  # docutils NO_EXE
            "rstpep2html.py",  # docutils NO_EXE
        ],
    },
    "b2": {
        "spec": "b2==3.12.0",
        "apps": _exe_if_win(["b2"]),
        "apps_of_dependencies": _exe_if_win(["docutils", "rst2ansi", "tabulate", "tqdm", "normalizer"])
        + [
            "activate-global-python-argcomplete",
            "python-argcomplete-check-easy-install-script",
            "register-python-argcomplete",
            "rst2html4.py",
            "rst2html5.py",
            "rst2html.py",
            "rst2latex.py",
            "rst2man.py",
            "rst2odt_prepstyles.py",
            "rst2odt.py",
            "rst2pseudoxml.py",
            "rst2s5.py",
            "rst2xetex.py",
            "rst2xml.py",
            "rstpep2html.py",
        ],
    },
    "beancount": {
        "spec": "beancount==2.3.6",
        "apps": _exe_if_win(
            [
                "bean-bake",
                "bean-check",
                "bean-doctor",
                "bean-example",
                "bean-extract",
                "bean-file",
                "bean-format",
                "bean-identify",
                "bean-price",
                "bean-query",
                "bean-report",
                "bean-sql",
                "bean-web",
                "treeify",
                "upload-to-sheets",
            ]
        ),
        "apps_of_dependencies": _exe_if_win(
            [
                "chardetect",  # chardet EXE
                "py.test",  # pytest EXE
                "pyrsa-decrypt",  # rsa EXE
                "pyrsa-encrypt",  # rsa EXE
                "pyrsa-keygen",  # rsa EXE
                "pyrsa-priv2pub",  # rsa EXE
                "pyrsa-sign",  # rsa EXE
                "pyrsa-verify",  # rsa EXE
                "pytest",  # pytest EXE
                "normalizer",
                "py.test",
            ]
        )
        + ["bottle.py", "dumppdf.py", "latin2ascii.py", "pdf2txt.py"],  # bottle NO_EXE
    },
    "beets": {
        "spec": "beets==1.4.9",
        "apps": _exe_if_win(["beet"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "mid3cp",
                "mid3iconv",
                "mid3v2",
                "moggsplit",
                "mutagen-inspect",
                "mutagen-pony",
                "unidecode",  # unidecode EXE
            ]
        ),
        "man_pages": [],
        "man_pages_of_dependencies": [
            str(Path("man1") / "mutagen-pony.1"),
            str(Path("man1") / "mutagen-inspect.1"),
            str(Path("man1") / "moggsplit.1"),
            str(Path("man1") / "mid3v2.1"),
            str(Path("man1") / "mid3iconv.1"),
            str(Path("man1") / "mid3cp.1"),
        ],
    },
    "black": {
        "spec": "black==22.8.0",
        "apps": _exe_if_win(["black", "blackd"]),
        "apps_of_dependencies": [],
    },
    "cactus": {
        "spec": "cactus==3.3.3",
        "apps": _exe_if_win(["cactus"]),
        "apps_of_dependencies": _exe_if_win(["keyring", "markdown2"])
        + [
            "asadmin",
            "bundle_image",
            "cfadmin",
            "cq",
            "cwutil",
            "django-admin.py",
            "dynamodb_dump",
            "dynamodb_load",
            "elbadmin",
            "fetch_file",
            "glacier",
            "instance_events",
            "keyring",
            "kill_instance",
            "launch_instance",
            "list_instances",
            "lss3",
            "mturk",
            "pyami_sendmail",
            "route53",
            "s3put",
            "sdbadmin",
            "taskadmin",
        ],
    },
    "chert": {
        "spec": "chert==19.1.0",
        "apps": _exe_if_win(["chert"]),
        "apps_of_dependencies": _exe_if_win(["ashes", "markdown_py"]) + ["ashes.py"],
    },
    "cloudtoken": {
        "spec": "cloudtoken==2.1.0",
        "apps": ["awstoken", "cloudtoken", "cloudtoken.app", "cloudtoken_proxy.sh"],
        "apps_of_dependencies": _exe_if_win(["flask", "keyring", "normalizer"]) + ["jp.py"],
    },
    "coala": {
        "spec": "coala==0.11.0",
        "apps": _exe_if_win(["coala", "coala-ci", "coala-delete-orig", "coala-format", "coala-json"]),
        "apps_of_dependencies": _exe_if_win(["normalizer", "pygmentize"]) + ["unidiff"],
    },
    "cookiecutter": {
        "spec": "cookiecutter==2.4.0",
        "apps": _exe_if_win(["cookiecutter"]),
        "apps_of_dependencies": _exe_if_win(["chardetect", "normalizer", "markdown-it", "pygmentize", "slugify"]),
    },
    "cython": {
        "spec": "cython==0.29.21",
        "apps": _exe_if_win(["cygdb", "cython", "cythonize"]),
        "apps_of_dependencies": [],
    },
    "datasette": {
        "spec": "datasette==0.50.2",
        "apps": _exe_if_win(["datasette"]),
        "apps_of_dependencies": _exe_if_win(["httpx", "hupper", "uvicorn"]) + ["pint-convert"],
    },
    "diffoscope": {
        "spec": "diffoscope==154",
        "apps": _exe_if_win(["diffoscope"]),
        "apps_of_dependencies": [],
    },
    "doc2dash": {
        "spec": "doc2dash==3.0.0",
        "apps": _exe_if_win(["doc2dash"]),
        "apps_of_dependencies": _exe_if_win(
            ["markdown-it", "pygmentize"]  # pygments EXE
        ),
    },
    "doitlive": {
        "spec": "doitlive==4.3.0",
        "apps": _exe_if_win(["doitlive"]),
        "apps_of_dependencies": [],
    },
    "gdbgui": {
        "spec": "gdbgui==0.14.0.1",
        "apps": _exe_if_win(["gdbgui"]),
        "apps_of_dependencies": _exe_if_win(["flask", "pygmentize"]),
    },
    "gns3-gui": {
        "spec": "gns3-gui==2.2.15",
        "apps": _exe_if_win(["gns3"]),
        "apps_of_dependencies": _exe_if_win(["distro", "jsonschema"]),
    },
    "grow": {
        "spec": "grow==1.0.0a10",
        "apps": ["grow"],
        "apps_of_dependencies": _exe_if_win(
            [
                "chardetect",  # chardet EXE
                "gen_protorpc",  # EXE
                "html2text",  # html2text EXE
                "markdown_py",  # Markdwon EXE
                "pybabel",  # babel EXE
                "pygmentize",  # pygments EXE
                "pyrsa-decrypt",  # rsa EXE
                "pyrsa-encrypt",  # rsa EXE
                "pyrsa-keygen",  # rsa EXE
                "pyrsa-priv2pub",  # rsa EXE
                "pyrsa-sign",  # rsa EXE
                "pyrsa-verify",  # rsa EXE
                "slugify",  # python_slugify EXE
                "watchmedo",  # watchdog EXE
            ]
        ),
    },
    "guake": {
        "spec": "guake==3.7.0",
        "apps": _exe_if_win(["guake", "guake-toggle"]),
        "apps_of_dependencies": _exe_if_win(["pbr"]),
    },
    "gunicorn": {
        "spec": "gunicorn==20.0.4",
        "apps": _exe_if_win(["gunicorn"]),
        "apps_of_dependencies": [],
    },
    "howdoi": {
        "spec": "howdoi==2.0.20",
        "apps": _exe_if_win(["howdoi"]),
        "apps_of_dependencies": _exe_if_win(["markdown-it", "keep", "normalizer", "pygmentize"]),
    },
    "httpie": {
        "spec": "httpie==3.2.2",
        "apps": _exe_if_win(["http", "httpie", "https"]),
        "apps_of_dependencies": _exe_if_win(["markdown-it", "normalizer", "pygmentize"]),
        "man_pages": [
            str(Path("man1") / "http.1"),
            str(Path("man1") / "httpie.1"),
            str(Path("man1") / "https.1"),
        ],
        "man_pages_of_dependencies": [],
    },
    "hyde": {
        "spec": "hyde==0.8.9",
        "apps": _exe_if_win(["hyde"]),
        "apps_of_dependencies": _exe_if_win(["markdown_py", "pygmentize"]) + ["smartypants"],
    },
    "ipython": {
        "spec": "ipython==7.16.1",
        "apps": _exe_if_win(["iptest", "iptest3", "ipython", "ipython3"]),
        "apps_of_dependencies": _exe_if_win(["pygmentize"]),  # pygments EXE
        "man_pages": [str(Path("man1") / "ipython.1.gz")],
        "man_pages_of_dependencies": [],
    },
    "isort": {
        "spec": "isort==5.6.4",
        "apps": _exe_if_win(["isort"]),
        "apps_of_dependencies": [],
    },
    "zest-releaser": {
        "spec": "zest.releaser==9.1.2",
        "apps": _exe_if_win(
            [
                "addchangelogentry",
                "bumpversion",
                "fullrelease",
                "lasttagdiff",
                "lasttaglog",
                "longtest",
                "postrelease",
                "prerelease",
                "release",
            ]
        ),
        "apps_of_dependencies": _exe_if_win(
            [
                "markdown-it",
                "normalizer",
                "twine",
                "pkginfo",
                "pyproject-build",
                "docutils",
                "pygmentize",
                "keyring",
            ]
        )
        + [
            "rst2html.py",
            "rst2html4.py",
            "rst2html5.py",
            "rst2latex.py",
            "rst2man.py",
            "rst2odt.py",
            "rst2odt_prepstyles.py",
            "rst2pseudoxml.py",
            "rst2s5.py",
            "rst2xetex.py",
            "rst2xml.py",
            "rstpep2html.py",
        ],
    },
    "jupyter": {
        "spec": "jupyter==1.0.0",
        "apps": [],
        "apps_of_dependencies": _exe_if_win(
            [
                "iptest",  # EXE
                "iptest3",  # EXE
                "ipython",  # EXE
                "ipython3",  # EXE
                "jsonschema",  # jsonschema EXE
                "jupyter",  # EXE
                "jupyter-bundlerextension",  # EXE
                "jupyter-console",  # EXE
                "jupyter-kernel",  # EXE
                "jupyter-kernelspec",  # EXE
                "jupyter-migrate",  # EXE
                "jupyter-nbconvert",  # EXE
                "jupyter-nbextension",  # EXE
                "jupyter-notebook",  # EXE
                "jupyter-qtconsole",  # EXE
                "jupyter-run",  # EXE
                "jupyter-serverextension",  # EXE
                "jupyter-troubleshoot",  # EXE
                "jupyter-trust",  # EXE
                "pygmentize",  # pygments EXE
            ]
        ),
    },
    "kaggle": {
        "spec": "kaggle==1.6.11",
        "apps": _exe_if_win(["kaggle"]),
        "apps_of_dependencies": list(set(_exe_if_win(["slugify", "normalizer", "tqdm"]))),
    },
    "kibitzr": {
        "spec": "kibitzr==7.0.5",
        "apps": _exe_if_win(["kibitzr"]),
        "apps_of_dependencies": _exe_if_win(["doesitcache", "httpx", "normalizer"]),
    },
    "klaus": {
        "spec": "klaus==1.5.2",
        "apps": ["klaus"],
        "apps_of_dependencies": _exe_if_win(["dulwich", "flask", "pygmentize"])
        + ["dul-receive-pack", "dul-upload-pack"],
    },
    "kolibri": {
        "spec": "kolibri==0.14.3",
        "apps": _exe_if_win(["kolibri"]),
        "apps_of_dependencies": [],
    },
    "lektor": {
        "spec": "Lektor==3.3.10",
        "apps": _exe_if_win(["lektor"]),
        "apps_of_dependencies": _exe_if_win(["filetype", "flask", "pybabel", "normalizer", "slugify", "watchmedo"])
        + ["EXIF.py"],
    },
    "localstack": {
        "spec": "localstack==0.12.1",
        "apps": ["localstack", "localstack.bat"],
        "apps_of_dependencies": _exe_if_win(
            [
                "dotenv",
                "markdown-it",
                "pbr",
                "pygmentize",
                "pyrsa-decrypt",
                "pyrsa-encrypt",
                "pyrsa-keygen",
                "pyrsa-priv2pub",
                "pyrsa-sign",
                "pyrsa-verify",
                "pysemver",
                "pytail",
                "tabulate",
                "normalizer",
            ]
        )
        + ["get_objgraph", "jp.py", "localstack-supervisor", "undill"],
    },
    "mackup": {
        "spec": "mackup==0.8.29",
        "apps": _exe_if_win(["mackup"]),
        "apps_of_dependencies": [],
    },  # ONLY FOR mac, linux
    "magic-wormhole": {
        "spec": "magic-wormhole==0.13.0",
        "apps": _exe_if_win(["wormhole"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "automat-visualize",  # EXE
                "cftp",  # EXE
                "ckeygen",  # EXE
                "conch",  # EXE
                "mailmail",  # EXE
                "pyhtmlizer",  # EXE
                "tkconch",  # EXE
                "tqdm",  # tqdm EXE
                "trial",  # EXE
                "twist",  # EXE
                "twistd",  # EXE
                "wamp",  # EXE
                "xbrnetwork",  # EXE
                "xbrnetwork-ui",  # EXE
            ]
        )
        + (["pywin32_postinstall.py", "pywin32_testall.py"] if WIN else []),
    },
    "mayan-edms": {
        "spec": "mayan-edms==3.5.2",
        "apps": ["mayan-edms.py"],
        "apps_of_dependencies": _exe_if_win(
            [
                "celery",  # EXE
                "chardetect",  # chardet EXE
                "django-admin",  # EXE
                "gunicorn",  # EXE
                "jsonschema",  # jsonschema EXE
                "sqlformat",  # sqlparse EXE
                "swagger-flex",  # EXE
                "update-tld-names",  # # EXE
            ]
        )
        + ["django-admin.py", "jsonpointer"],
    },
    "mkdocs": {
        "spec": "mkdocs==1.1.2",
        "apps": _exe_if_win(["mkdocs"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "livereload",  # EXE
                "futurize",  # future EXE
                "pasteurize",  # future EXE
                "nltk",  # EXE
                "tqdm",  # tqdm EXE
                "markdown_py",  # Markdwon EXE
            ]
        ),
    },
    "mycli": {
        "spec": "mycli==1.22.2",
        "apps": _exe_if_win(["mycli"]),
        "apps_of_dependencies": _exe_if_win(["pygmentize", "sqlformat", "tabulate"]),
    },
    "nikola": {
        "spec": "nikola==8.2.4",
        "apps": _exe_if_win(["nikola"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "docutils",
                "doit",  # EXE
                "mako-render",  # mako EXE
                "markdown_py",  # Markdwon EXE
                "natsort",  # EXE
                "pybabel",  # babel EXE
                "pygmentize",  # pygments EXE
                "unidecode",  # unidecode EXE
                "normalizer",
            ]
        )
        + [
            "rst2html.py",  # docutils NO_EXE
            "rst2html4.py",  # docutils NO_EXE
            "rst2html5.py",  # docutils NO_EXE
            "rst2latex.py",  # docutils NO_EXE
            "rst2man.py",  # docutils NO_EXE
            "rst2odt.py",  # docutils NO_EXE
            "rst2odt_prepstyles.py",  # docutils NO_EXE
            "rst2pseudoxml.py",  # docutils NO_EXE
            "rst2s5.py",  # docutils NO_EXE
            "rst2xetex.py",  # docutils NO_EXE
            "rst2xml.py",  # docutils NO_EXE
            "rstpep2html.py",  # docutils NO_EXE
        ],
        "man_pages": [str(Path("man1") / "nikola.1.gz")],
        "man_pages_of_dependencies": [],
    },
    "nox": {
        "spec": "nox==2023.4.22",
        "apps": _exe_if_win(["nox", "tox-to-nox"]),
        "apps_of_dependencies": _exe_if_win(["virtualenv"])
        + [
            "activate-global-python-argcomplete",
            "python-argcomplete-check-easy-install-script",
            "register-python-argcomplete",
        ],  # from argcomplete
    },
    "pbr": {"spec": "pbr==5.6.0", "apps": _exe_if_win(["pbr"])},
    "pelican": {
        "spec": "pelican==4.8.0",
        "apps": _exe_if_win(
            [
                "pelican",
                "pelican-import",
                "pelican-plugins",
                "pelican-quickstart",
                "pelican-themes",
            ]
        ),
        "apps_of_dependencies": _exe_if_win(["docutils", "markdown-it", "pygmentize", "unidecode"])
        + [
            "rst2html.py",  # docutils NO_EXE
            "rst2html4.py",  # docutils NO_EXE
            "rst2html5.py",  # docutils NO_EXE
            "rst2latex.py",  # docutils NO_EXE
            "rst2man.py",  # docutils NO_EXE
            "rst2odt.py",  # docutils NO_EXE
            "rst2odt_prepstyles.py",  # docutils NO_EXE
            "rst2pseudoxml.py",  # docutils NO_EXE
            "rst2s5.py",  # docutils NO_EXE
            "rst2xetex.py",  # docutils NO_EXE
            "rst2xml.py",  # docutils NO_EXE
            "rstpep2html.py",  # docutils NO_EXE
        ],
    },
    "platformio": {
        "spec": "platformio==6.1.11",
        "apps": _exe_if_win(["pio", "piodebuggdb", "platformio"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "async-json-rpc-server",
                "pyserial-miniterm",
                "pyserial-ports",
                "tabulate",
                "uvicorn",
                "normalizer",
            ]
        )
        + ["bottle.py", "readelf.py"],
    },
    "ppci": {
        "spec": "ppci==0.5.8",
        "apps": _exe_if_win(
            [
                "ppci-archive",
                "ppci-asm",
                "ppci-build",
                "ppci-c3c",
                "ppci-cc",
                "ppci-dbg",
                "ppci-disasm",
                "ppci-hexdump",
                "ppci-hexutil",
                "ppci-java",
                "ppci-ld",
                "ppci-llc",
                "ppci-mkuimage",
                "ppci-objcopy",
                "ppci-objdump",
                "ppci-ocaml",
                "ppci-opt",
                "ppci-pascal",
                "ppci-pedump",
                "ppci-pycompile",
                "ppci-readelf",
                "ppci-wabt",
                "ppci-wasm2wat",
                "ppci-wasmcompile",
                "ppci-wat2wasm",
                "ppci-yacc",
            ]
        ),
        "apps_of_dependencies": [],
    },
    "prosopopee": {
        "spec": "prosopopee==1.1.3",
        "apps": _exe_if_win(["prosopopee"]),
        "apps_of_dependencies": _exe_if_win(["futurize", "pasteurize", "pybabel"]),
    },
    "ptpython": {
        "spec": "ptpython==3.0.7",
        "apps": _exe_if_win(
            [
                "ptipython",
                "ptipython3",
                "ptipython3.8",
                "ptpython",
                "ptpython3",
                "ptpython3.8",
            ]
        ),
        "apps_of_dependencies": _exe_if_win(["pygmentize"]),  # pygments EXE
    },
    "pycowsay": {
        "spec": "pycowsay==0.0.0.2",
        "apps": _exe_if_win(["pycowsay"]),
        "apps_of_dependencies": [],
        "man_pages": [str(Path("man6") / "pycowsay.6")],
        "man_pages_of_dependencies": [],
    },
    "pygdbmi": {"spec": "pygdbmi==0.10.0.0", "apps": [], "apps_of_dependencies": []},
    "pylint": {
        "spec": "pylint==3.0.4",
        "apps": _exe_if_win(["pylint", "pylint-config", "pyreverse", "symilar"]),
        "apps_of_dependencies": _exe_if_win(["isort", "isort-identify-imports"])
        + ["get_gprof", "get_objgraph", "undill"],
    },
    "retext": {
        "spec": "ReText==8.0.1",
        "apps": _exe_if_win(["retext"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "docutils",
                "markdown_py",  # Markdwon EXE
                "pygmentize",  # pygments EXE
                "pylupdate6",  # EXE
                "pyuic6",  # EXE
                "chardetect",
            ]
        )
        + [
            "rst2html.py",  # docutils NO_EXE
            "rst2html4.py",  # docutils NO_EXE
            "rst2html5.py",  # docutils NO_EXE
            "rst2latex.py",  # docutils NO_EXE
            "rst2man.py",  # docutils NO_EXE
            "rst2odt.py",  # docutils NO_EXE
            "rst2odt_prepstyles.py",  # docutils NO_EXE
            "rst2pseudoxml.py",  # docutils NO_EXE
            "rst2s5.py",  # docutils NO_EXE
            "rst2xetex.py",  # docutils NO_EXE
            "rst2xml.py",  # docutils NO_EXE
            "rstpep2html.py",  # docutils NO_EXE
        ],
    },
    "robotframework": {
        "spec": "robotframework==3.2.2",
        "apps": _exe_if_win(["rebot", "robot"]),
        "apps_of_dependencies": [],
    },
    "shell-functools": {
        "spec": "shell-functools==0.3.0",
        "apps": [
            "filter",
            "foldl",
            "foldl1",
            "ft-functions",
            "map",
            "sort_by",
            "take_while",
        ],
        "apps_of_dependencies": [],
    },
    "speedtest-cli": {
        "spec": "speedtest-cli==2.1.2",
        "apps": _exe_if_win(["speedtest", "speedtest-cli"]),
        "apps_of_dependencies": [],
    },
    "sphinx": {
        "spec": "Sphinx==7.2.6",
        "apps": _exe_if_win(["sphinx-apidoc", "sphinx-autogen", "sphinx-build", "sphinx-quickstart"]),
        "apps_of_dependencies": _exe_if_win(["docutils", "pybabel", "normalizer", "pygmentize"])
        + [
            "rst2html.py",  # docutils NO_EXE
            "rst2html4.py",  # docutils NO_EXE
            "rst2html5.py",  # docutils NO_EXE
            "rst2latex.py",  # docutils NO_EXE
            "rst2man.py",  # docutils NO_EXE
            "rst2odt.py",  # docutils NO_EXE
            "rst2odt_prepstyles.py",  # docutils NO_EXE
            "rst2pseudoxml.py",  # docutils NO_EXE
            "rst2s5.py",  # docutils NO_EXE
            "rst2xetex.py",  # docutils NO_EXE
            "rst2xml.py",  # docutils NO_EXE
            "rstpep2html.py",  # docutils NO_EXE
        ],
    },
    "sqlmap": {
        "spec": "sqlmap==1.4.10",
        "apps": _exe_if_win(["sqlmap"]),
        "apps_of_dependencies": [],
    },
    "streamlink": {
        "spec": "streamlink==6.3.1",
        "apps": _exe_if_win(["streamlink"] + (["streamlinkw"] if WIN else [])),
        "apps_of_dependencies": _exe_if_win(["normalizer", "wsdump"]),
        "man_pages": [str(Path("man1") / "streamlink.1")],
        "man_pages_of_dependencies": [],
    },
    "taguette": {
        "spec": "taguette==0.9.2",
        "apps": _exe_if_win(["taguette"]),
        "apps_of_dependencies": _exe_if_win(["alembic", "mako-render"]) + ["vba_extract.py"],
    },
    "term2048": {
        "spec": "term2048==0.2.7",
        "apps": _exe_if_win(["term2048"]),
        "apps_of_dependencies": [],
    },
    "tox-ini-fmt": {
        "spec": "tox-ini-fmt==0.5.0",
        "apps": _exe_if_win(["tox-ini-fmt"]),
        "apps_of_dependencies": _exe_if_win(["py.test", "pytest"]),  # pytest EXE
    },
    "visidata": {
        "spec": "visidata==2.0.1",
        "apps": _exe_if_win(["visidata"]) + ["vd"],
        "apps_of_dependencies": [],
        "man_pages": [str(Path("man1") / "vd.1")],
        "man_pages_of_dependencies": [],
    },
    "vulture": {
        "spec": "vulture==2.1",
        "apps": _exe_if_win(["vulture"]),
        "apps_of_dependencies": [],
    },
    "weblate": {
        "spec": "Weblate==4.3.1",
        "apps": _exe_if_win(["weblate"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win (can't install)
            [
                "borg",
                "borgfs",
                "build_firefox.sh",
                "build_tmdb",
                "buildxpi.py",
                "celery",
                "chardetect",  # chardet EXE
                "csv2po",
                "csv2tbx",
                "cygdb",
                "cython",
                "cythonize",
                "django-admin",
                "django-admin.py",  # NO_EXE
                "flatxml2po",
                "get_moz_enUS.py",
                "html2po",
                "html2text",  # html2text EXE
                "ical2po",
                "idml2po",
                "ini2po",
                "json2po",
                "jsonschema",  # jsonschema EXE
                "junitmsgfmt",
                "misaka",
                "moz2po",
                "mozlang2po",
                "odf2xliff",
                "oo2po",
                "oo2xliff",
                "php2po",
                "phppo2pypo",
                "po2csv",
                "po2flatxml",
                "po2html",
                "po2ical",
                "po2idml",
                "po2ini",
                "po2json",
                "po2moz",
                "po2mozlang",
                "po2oo",
                "po2php",
                "po2prop",
                "po2rc",
                "po2resx",
                "po2sub",
                "po2symb",
                "po2tiki",
                "po2tmx",
                "po2ts",
                "po2txt",
                "po2web2py",
                "po2wordfast",
                "po2xliff",
                "po2yaml",
                "poclean",
                "pocommentclean",
                "pocompendium",
                "pocompile",
                "poconflicts",
                "pocount",
                "podebug",
                "pofilter",
                "pogrep",
                "pomerge",
                "pomigrate2",
                "popuretext",
                "poreencode",
                "porestructure",
                "posegment",
                "posplit",
                "poswap",
                "pot2po",
                "poterminology",
                "pretranslate",
                "prop2po",
                "pydiff",
                "pypo2phppo",
                "rc2po",
                "resx2po",
                "sqlformat",  # sqlparse EXE
                "sub2po",
                "symb2po",
                "tbx2po",
                "tiki2po",
                "tmserver",
                "ts2po",
                "txt2po",
                "web2py2po",
                "weblate-discover",
                "xliff2odf",
                "xliff2oo",
                "xliff2po",
                "yaml2po",
            ]
        ),
    },
    "youtube-dl": {
        "spec": "youtube-dl==2020.9.20",
        "apps": _exe_if_win(["youtube-dl"]),
        "apps_of_dependencies": [],
        "man_pages": [str(Path("man1") / "youtube-dl.1")],
        "man_pages_of_dependencies": [],
    },
    "zeo": {
        "spec": "ZEO==5.2.2",
        "apps": _exe_if_win(["runzeo", "zeo-nagios", "zeoctl", "zeopack"]),
        "apps_of_dependencies": _exe_if_win(
            [
                "fsdump",
                "fsoids",
                "fsrefs",
                "fstail",
                "repozo",
                "zconfig",
                "zconfig_schema2html",
                "zdaemon",
            ]
        ),
    },
}
