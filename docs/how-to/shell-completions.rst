##################
 Shell completions
##################

Enable tab completion for pipx and for the apps it installs.

***********************
 Enable pipx completion
***********************

Print the instructions for your shell and follow them:

.. code-block:: console

    $ pipx completions

*******************************
 Completions for installed apps
*******************************

A package can ship the completion script for its own command, the way it ships a man page. pipx links that script out
of the environment it installed into, so the completions arrive with the package and leave with it.

pipx picks up the three directories a wheel installs completion scripts into and links each under
``PIPX_COMPLETION_DIR`` (default ``~/.local/share``):

.. list-table::
    :header-rows: 1
    :widths: 34 44 22

    - - Shipped by the package
      - Linked to
      - Loaded by
    - - ``share/bash-completion/completions/``
      - ``~/.local/share/bash-completion/completions/``
      - bash, on its own
    - - ``share/fish/vendor_completions.d/``
      - ``~/.local/share/fish/vendor_completions.d/``
      - fish, on its own
    - - ``share/zsh/site-functions/``
      - ``~/.local/share/zsh/site-functions/``
      - zsh, once you say so

bash and fish read their directories without further help. zsh needs the directory on its ``fpath``, so add this to
``~/.zshrc`` ahead of the call to ``compinit``:

.. code-block:: bash

    fpath+=("$(pipx environment --value PIPX_COMPLETION_DIR)/zsh/site-functions")

``pipx uninstall`` takes the links away, and ``pipx unexpose`` removes them while leaving the package in place (see
:doc:`expose-apps`).

***********************************
 Ship completions from your package
***********************************

Install completion scripts through your build backend's data files. With setuptools:

.. code-block:: python

    setup(
        name="your-tool",
        data_files=[
            ("share/bash-completion/completions", ["completions/your-tool"]),
            ("share/zsh/site-functions", ["completions/_your-tool"]),
            ("share/fish/vendor_completions.d", ["completions/your-tool.fish"]),
        ],
    )

**********
 Verify it
**********

Open a new shell and press ``Tab`` after typing ``pipx``. The subcommands complete when the setup took effect.
