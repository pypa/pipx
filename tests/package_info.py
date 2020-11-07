import sys
from typing import Any, Dict

WIN = sys.platform.startswith("win")


def _exe_if_win(apps):
    app_strings = []
    app_strings = [f"{app}.exe" if WIN else app for app in apps]
    return app_strings


# Versions of all packages possibly used in our tests
# Only apply _app_names to entry_points, NOT scripts!
PKG: Dict[str, Dict[str, Any]] = {
    "ansible": {
        "spec": "ansible==2.9.13",
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
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "jp.py",
                "pyrsa-decrypt",
                "pyrsa-encrypt",
                "pyrsa-keygen",
                "pyrsa-priv2pub",
                "pyrsa-sign",
                "pyrsa-verify",
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
            ]
        ),
    },
    "b2": {
        "spec": "b2==2.0.2",
        "apps": _exe_if_win(["b2"]),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "tqdm"]
        ),  # TODO: check if _exe_if_win
    },
    "beancount": {
        "spec": "beancount==2.3.3",
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
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "bottle.py",
                "chardetect",
                "py.test",
                "pyrsa-decrypt",
                "pyrsa-encrypt",
                "pyrsa-keygen",
                "pyrsa-priv2pub",
                "pyrsa-sign",
                "pyrsa-verify",
                "pytest",
            ]
        ),
    },
    "beets": {
        "spec": "beets==1.4.9",
        "apps": _exe_if_win(["beet"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "mid3cp",
                "mid3iconv",
                "mid3v2",
                "moggsplit",
                "mutagen-inspect",
                "mutagen-pony",
                "unidecode",
            ]
        ),
    },
    "black": {
        "spec": "black==20.8b1",
        "apps": _exe_if_win(["black", "black-primer", "blackd"]),
        "apps_of_dependencies": [],
    },
    "cactus": {
        "spec": "cactus==3.3.3",
        "apps": _exe_if_win(["cactus"]),
        "apps_of_dependencies": _exe_if_win(
            [
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
                "markdown2",
                "mturk",
                "pyami_sendmail",
                "route53",
                "s3put",
                "sdbadmin",
                "taskadmin",
            ]
        ),
    },
    "chert": {
        "spec": "chert==19.1.0",
        "apps": _exe_if_win(["chert"]),
        "apps_of_dependencies": _exe_if_win(
            ["ashes", "ashes.py", "markdown_py"]
        ),  # TODO: check if _exe_if_win
    },
    "cloudtoken": {
        "spec": "cloudtoken==0.1.707",
        "apps": ["cloudtoken", "cloudtoken.app", "cloudtoken_proxy.sh", "awstoken"],
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["chardetect", "flask", "jp.py", "keyring"]
        ),
    },
    "coala": {
        "spec": "coala==0.11.0",
        "apps": _exe_if_win(
            ["coala", "coala-ci", "coala-delete-orig", "coala-format", "coala-json"]
        ),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "pygmentize", "unidiff"]
        ),  # TODO: check if _exe_if_win
    },
    "cookiecutter": {
        "spec": "cookiecutter==1.7.2",
        "apps": _exe_if_win(["cookiecutter"]),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "slugify"]
        ),  # TODO: check if _exe_if_win
    },
    "cython": {
        "spec": "cython==0.29.21",
        "apps": _exe_if_win(["cygdb", "cython", "cythonize"]),
        "apps_of_dependencies": [],
    },
    "datasette": {
        "spec": "datasette==0.50.2",
        "apps": _exe_if_win(["datasette"]),
        "apps_of_dependencies": _exe_if_win(
            ["hupper", "pint-convert" "uvicorn"]
        ),  # TODO: check if _exe_if_win
    },
    "diffoscope": {
        "spec": "diffoscope==154",
        "apps": _exe_if_win(["diffoscope"]),
        "apps_of_dependencies": [],
    },
    "doc2dash": {
        "spec": "doc2dash==2.3.0",
        "apps": _exe_if_win(["doc2dash"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "chardetect",
                "pybabel",
                "pygmentize",
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
                "sphinx-apidoc",
                "sphinx-autogen",
                "sphinx-build",
                "sphinx-quickstart",
            ]
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
        "apps_of_dependencies": _exe_if_win(
            ["flask", "pygmentize"]
        ),  # TODO: check if _exe_if_win
    },
    "gns3-gui": {
        "spec": "gns3-gui==2.2.15",
        "apps": _exe_if_win(["gns3"]),
        "apps_of_dependencies": _exe_if_win(
            ["distro", "jsonschema"]
        ),  # TODO: check if _exe_if_win
    },
    "grow": {
        "spec": "grow==1.0.0a10",
        "apps": ["grow"],
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "chardetect",
                "gen_protorpc",
                "html2text",
                "markdown_py",
                "pybabel",
                "pygmentize",
                "pyrsa-decrypt",
                "pyrsa-encrypt",
                "pyrsa-keygen",
                "pyrsa-priv2pub",
                "pyrsa-sign",
                "pyrsa-verify",
                "slugify",
                "watchmedo",
            ]
        ),
    },
    "guake": {
        "spec": "guake==3.7.0",
        "apps": _exe_if_win(["guake", "guake-toggle"]),
        "apps_of_dependencies": _exe_if_win(["pbr"]),  # TODO: check if _exe_if_win
    },
    "gunicorn": {
        "spec": "gunicorn==20.0.4",
        "apps": _exe_if_win(["gunicorn"]),
        "apps_of_dependencies": [],
    },
    "howdoi": {
        "spec": "howdoi==2.0.7",
        "apps": _exe_if_win(["howdoi"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["chardetect", "keep", "pygmentize", "pyjwt"]
        ),
    },
    "httpie": {
        "spec": "httpie==2.3.0",
        "apps": _exe_if_win(["http", "https"]),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "pygmentize"]
        ),  # TODO: check if _exe_if_win
    },
    "hyde": {
        "spec": "hyde==0.8.9",
        "apps": _exe_if_win(["hyde"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["markdown_py", "pygmentize", "smartypants"]
        ),
    },
    "ipython": {
        "spec": "ipython==7.16.1",
        "apps": _exe_if_win(["iptest", "iptest3", "ipython", "ipython3"]),
        "apps_of_dependencies": _exe_if_win(
            ["pygmentize"]
        ),  # TODO: check if _exe_if_win
    },
    "isort": {
        "spec": "isort==5.6.4",
        "apps": _exe_if_win(["isort"]),
        "apps_of_dependencies": [],
    },
    "jaraco-financial": {
        "spec": "jaraco.financial==2.0",
        "apps": _exe_if_win(
            [
                "clean-msmoney-temp",
                "fix-qif-date-format",
                "launch-in-money",
                "ofx",
                "record-document-hashes",
            ]
        ),
        "apps_of_dependencies": _exe_if_win(
            ["keyring", "chardetect", "calc-prorate"]
        ),  # TODO: check if _exe_if_win
    },
    "jupyter": {
        "spec": "jupyter==1.0.0",
        "apps": [],
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "iptest",
                "iptest3",
                "ipython",
                "ipython3",
                "jsonschema",
                "jupyter",
                "jupyter-bundlerextension",
                "jupyter-console",
                "jupyter-kernel",
                "jupyter-kernelspec",
                "jupyter-migrate",
                "jupyter-nbconvert",
                "jupyter-nbextension",
                "jupyter-notebook",
                "jupyter-qtconsole",
                "jupyter-run",
                "jupyter-serverextension",
                "jupyter-troubleshoot",
                "jupyter-trust",
                "pygmentize",
            ]
        ),
    },
    "kaggle": {
        "spec": "kaggle==1.5.9",
        "apps": _exe_if_win(["kaggle"]),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "slugify", "tqdm"]
        ),  # TODO: check if _exe_if_win
    },
    "kibitzr": {
        "spec": "kibitzr==6.0.0",
        "apps": _exe_if_win(["kibitzr"]),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "doesitcache"]
        ),  # TODO: check if _exe_if_win
    },
    "klaus": {
        "spec": "klaus==1.5.2",
        "apps": ["klaus"],
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["dul-receive-pack", "dul-upload-pack", "dulwich", "flask", "pygmentize"]
        ),
    },
    "kolibri": {
        "spec": "kolibri==0.14.3",
        "apps": _exe_if_win(["kolibri"]),
        "apps_of_dependencies": [],
    },
    "lektor": {
        "spec": "Lektor==3.2.0",
        "apps": _exe_if_win(["lektor"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["EXIF.py", "chardetect", "flask", "pybabel", "slugify", "watchmedo"]
        ),
    },
    "localstack": {
        "spec": "localstack==0.12.1",
        "apps": ["localstack", "localstack.bat"],
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "jp.py"]
        ),  # TODO: check if _exe_if_win
    },
    "mackup": {
        "spec": "mackup==0.8.29",
        "apps": _exe_if_win(["mackup"]),
        "apps_of_dependencies": [],
    },  # ONLY FOR mac, linux
    "magic-wormhole": {
        "spec": "magic-wormhole==0.12.0",
        "apps": _exe_if_win(["wormhole"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "automat-visualize",
                "cftp",
                "ckeygen",
                "conch",
                "mailmail",
                "pyhtmlizer",
                "tkconch",
                "tqdm",
                "trial",
                "twist",
                "twistd",
                "wamp",
                "xbrnetwork",
            ]
        ),
    },
    "mayan-edms": {
        "spec": "mayan-edms==3.5.2",
        "apps": ["mayan-edms.py"],
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "celery",
                "chardetect",
                "django-admin",
                "django-admin.py",
                "gunicorn",
                "jsonpointer",
                "jsonschema",
                "sqlformat",
                "swagger-flex",
                "update-tld-names",
            ]
        ),
    },
    "mkdocs": {
        "spec": "mkdocs==1.1.2",
        "apps": _exe_if_win(["mkdocs"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["livereload", "futurize", "pasteurize", "nltk", "tqdm", "markdown_py"]
        ),
    },
    "mycli": {
        "spec": "mycli==1.22.2",
        "apps": _exe_if_win(["mycli"]),
        "apps_of_dependencies": _exe_if_win(
            ["pygmentize", "sqlformat", "tabulate"]
        ),  # TODO: check if _exe_if_win
    },
    "nikola": {
        "spec": "nikola==8.1.1",
        "apps": _exe_if_win(["nikola"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "chardetect",
                "doit",
                "mako-render",
                "markdown_py",
                "natsort",
                "pybabel",
                "pygmentize",
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
                "unidecode",
            ]
        ),
    },
    "nox": {
        "spec": "nox==2020.8.22",
        "apps": _exe_if_win(["nox", "tox-to-nox"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "activate-global-python-argcomplete",
                "python-argcomplete-check-easy-install-script",
                "python-argcomplete-tcsh",
                "register-python-argcomplete",
                "virtualenv",
            ]
        ),  # TODO: are some of these not real?
    },
    "pelican": {
        "spec": "pelican==4.5.0",
        "apps": _exe_if_win(
            [
                "pelican",
                "pelican-import",
                "pelican-plugins",
                "pelican-quickstart",
                "pelican-themes",
            ]
        ),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "pygmentize",
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
                "unidecode",
            ]
        ),
    },
    "platformio": {
        "spec": "platformio==5.0.1",
        "apps": _exe_if_win(["pio", "piodebuggdb", "platformio"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "bottle.py",
                "chardetect",
                "miniterm.py",
                "miniterm.pyc",
                "readelf.py",
                "tabulate",
            ]
        ),
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
        "apps_of_dependencies": _exe_if_win(
            ["futurize", "pasteurize", "pybabel"]
        ),  # TODO: check if _exe_if_win
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
        "apps_of_dependencies": _exe_if_win(
            ["pygmentize"]
        ),  # TODO: check if _exe_if_win
    },
    "pycowsay": {
        "spec": "pycowsay==0.0.0.1",
        "apps": _exe_if_win(["pycowsay"]),
        "apps_of_dependencies": [],
    },
    "pylint": {
        "spec": "pylint==2.3.1",
        "apps": _exe_if_win(["epylint", "pylint", "pyreverse", "symilar"]),
        "apps_of_dependencies": _exe_if_win(["isort"]),  # TODO: check if _exe_if_win
    },
    "retext": {
        "spec": "ReText==7.1.0",
        "apps": _exe_if_win(["retext"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "chardetect",
                "markdown_py",
                "pygmentize",
                "pylupdate5",
                "pyrcc5",
                "pyuic5",
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
            ]
        ),
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
        "spec": "Sphinx==3.2.1",
        "apps": _exe_if_win(
            ["sphinx-apidoc", "sphinx-autogen", "sphinx-build", "sphinx-quickstart"]
        ),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "chardetect",
                "pybabel",
                "pygmentize",
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
            ]
        ),
    },
    "sqlmap": {
        "spec": "sqlmap==1.4.10",
        "apps": _exe_if_win(["sqlmap"]),
        "apps_of_dependencies": [],
    },
    "streamlink": {
        "spec": "streamlink==1.7.0",
        "apps": _exe_if_win(["streamlink"] + ["streamlinkw"] if WIN else []),
        "apps_of_dependencies": _exe_if_win(
            ["chardetect", "wsdump.py"]
        ),  # TODO: check if _exe_if_win
    },
    "taguette": {
        "spec": "taguette==0.9.2",
        "apps": _exe_if_win(["taguette"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            ["alembic", "mako-render", "vba_extract.py"]
        ),
    },
    "term2048": {
        "spec": "term2048==0.2.7",
        "apps": _exe_if_win(["term2048"]),
        "apps_of_dependencies": [],
    },
    "tox-ini-fmt": {
        "spec": "tox-ini-fmt==0.5.0",
        "apps": _exe_if_win(["tox-ini-fmt"]),
        "apps_of_dependencies": _exe_if_win(
            ["py.test", "pytest"]
        ),  # TODO: check if _exe_if_win
    },
    "visidata": {
        "spec": "visidata==2.0.1",
        "apps": _exe_if_win(["visidata"]) + ["vd"],
        "apps_of_dependencies": [],
    },
    "vulture": {
        "spec": "vulture==2.1",
        "apps": _exe_if_win(["vulture"]),
        "apps_of_dependencies": [],
    },
    "weblate": {
        "spec": "Weblate==4.3.1",
        "apps": _exe_if_win(["weblate"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
            [
                "borg",
                "borgfs",
                "build_firefox.sh",
                "build_tmdb",
                "buildxpi.py",
                "celery",
                "chardetect",
                "csv2po",
                "csv2tbx",
                "cygdb",
                "cython",
                "cythonize",
                "django-admin",
                "django-admin.py",
                "flatxml2po",
                "get_moz_enUS.py",
                "html2po",
                "html2text",
                "ical2po",
                "idml2po",
                "ini2po",
                "json2po",
                "jsonschema",
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
                "pyjwt",
                "pypo2phppo",
                "rc2po",
                "resx2po",
                "sqlformat",
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
    },
    "zeo": {
        "spec": "ZEO==5.2.2",
        "apps": _exe_if_win(["runzeo", "zeo-nagios", "zeoctl", "zeopack"]),
        "apps_of_dependencies": _exe_if_win(  # TODO: check if _exe_if_win
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
