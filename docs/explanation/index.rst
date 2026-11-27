#############
 Explanation
#############

Design rationale and background. Read these to understand *why* pipx works the way it does.

-  :doc:`how-pipx-works` covers the virtual-environment architecture, the shared `pip <https://pip.pypa.io>`_ library,
   and how apps reach your ``PATH``.
-  :doc:`scope` sets the application model and the boundaries for configuration, discovery, and distribution.
-  :doc:`comparisons` relates pipx to ``pip``, `uv tool <https://docs.astral.sh/uv/concepts/tools/>`_, `Poetry
   <https://python-poetry.org>`_, `pipenv <https://pipenv.pypa.io>`_, `pyenv <https://github.com/pyenv/pyenv>`_, `brew
   <https://brew.sh>`_, `npx <https://docs.npmjs.com/cli/commands/npx>`_, and more.
-  :doc:`making-packages-compatible` explains how to create packages so that shipped apps, man pages and shell completions
   are automatically made available to the user when installing the package with pipx

.. toctree::
    :hidden:

    how-pipx-works
    scope
    comparisons
    making-packages-compatible
