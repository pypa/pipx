######
 pipx
######

``pipx`` installs and runs end-user Python applications in isolated environments. It fills the same role as macOS's
``brew``, JavaScript's `npx <https://docs.npmjs.com/cli/commands/npx>`_, and Linux's ``apt``. Under the hood it uses
pip, but unlike pip it creates a separate virtual environment for each application, so their dependencies never collide
and an uninstall leaves nothing behind.

.. mermaid::

    flowchart LR
        USER["you"] -->|"pipx install"| PIPX["pipx"]
        USER -->|"pipx run"| PIPX
        PIPX -->|"fetches from"| PYPI["PyPI"]
        PIPX -->|"creates"| VENV["isolated venvs"]
        VENV -->|"exposes on PATH"| APPS["black, ruff,<br/>poetry, ..."]

        classDef you fill:#3f72af,stroke:#28507d,color:#fff;
        classDef pipx fill:#2a9d8f,stroke:#1f7268,color:#fff;
        classDef src fill:#c78c20,stroke:#946716,color:#fff;
        classDef venv fill:#7c4dff,stroke:#5a34c0,color:#fff;
        classDef apps fill:#388e3c,stroke:#276628,color:#fff;
        class USER you;
        class PIPX pipx;
        class PYPI src;
        class VENV venv;
        class APPS apps;

************
 Start here
************

.. grid:: 1 2 2 2
    :gutter: 3

    .. grid-item-card:: Tutorials
        :link: tutorial/index
        :link-type: doc

        Install your first application and run one in a throwaway environment, one step at a time.

    .. grid-item-card:: How-to guides
        :link: how-to/index
        :link-type: doc

        Task recipes for installing pipx, injecting packages, pinning versions, configuring paths, and more.

    .. grid-item-card:: Reference
        :link: reference/index
        :link-type: doc

        The full CLI, environment variables, exit codes, the JSON envelope, and worked examples.

    .. grid-item-card:: Explanation
        :link: explanation/index
        :link-type: doc

        How pipx works, what it manages on disk, and how it compares to other tools.

*************
 pip vs pipx
*************

pip installs both libraries and applications into whatever environment is active, with no isolation. pipx installs
only applications, each in its own virtual environment, and exposes their commands on your ``PATH``. You get clean
uninstalls, zero dependency conflicts between tools, and no ``sudo pip install`` — pipx runs with regular user
permissions.

**********************
 Where apps come from
**********************

pipx pulls packages from `PyPI <https://pypi.org/>`_ by default, but accepts any source pip supports: local
directories, wheels, and git URLs. Any package that declares `console script entry points
<https://packaging.python.org/en/latest/specifications/entry-points/>`_ works with pipx.
`Poetry <https://python-poetry.org/docs/pyproject/#scripts>`_ and `Hatch
<https://hatch.pypa.io/latest/config/metadata/#cli>`_ users can add entry points the same way.

***********
 Highlights
***********

- Install CLI apps into isolated environments with ``pipx install``, so there are no dependency conflicts and uninstalls
  are clean.
- List, upgrade, and uninstall managed apps in one command.
- Run the latest version of any app in a temporary environment with ``pipx run``, without installing it first.

**************
 Testimonials
**************

    "Thanks for improving the workflow that pipsi has covered in the past. Nicely done!"

    — *Jannis Leidel, PSF fellow, former pip and Django core developer, and founder of the Python Packaging Authority
    (PyPA)*

    "My setup pieces together pyenv, poetry, and pipx. [...] For the things I need, it's perfect."

    — *Jacob Kaplan-Moss, co-creator of Django, in* `My Python Development Environment, 2020 Edition
    <https://jacobian.org/2019/nov/11/python-environment-2020/>`_

    "I'm a big fan of pipx. I think pipx is super cool."

    — *Michael Kennedy, co-host of the PythonBytes podcast, in* `episode 139
    <https://pythonbytes.fm/episodes/transcript/139/f-yes-for-the-f-strings>`_

*********
 Credits
*********

pipx was inspired by `pipsi <https://github.com/mitsuhiko/pipsi>`_ and `npx <https://github.com/npm/npx>`_. It was
created by `Chad Smith <https://github.com/cs01/>`_ and has had lots of help from `contributors
<https://github.com/pypa/pipx/graphs/contributors>`_. The logo was created by `@IrishMorales
<https://github.com/IrishMorales>`_.

pipx is maintained by a team of volunteers (in alphabetical order): `Bernát Gábor
<https://github.com/gaborbernat>`_, `Chad Smith <https://github.com/cs01>`_ (co-lead), `Chrysle
<https://github.com/chrysle>`_, `Jason Lam <https://github.com/dukecat0>`_, `Matthew Clapp
<https://github.com/itsayellow>`_ (co-lead), `Robert Offner <https://github.com/gitznik>`_, and `Tzu-ping Chung
<https://github.com/uranusjr>`_.

The documentation follows the `Diátaxis <https://diataxis.fr>`_ framework.

.. toctree::
    :hidden:
    :maxdepth: 2

    tutorial/index
    how-to/index
    reference/index
    explanation/index
    contributing
    changelog
