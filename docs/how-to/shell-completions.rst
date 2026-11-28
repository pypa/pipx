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

To check the setup, open a new shell and press ``Tab`` after typing ``pipx``. The shell lists the pipx subcommands.

*******************************
 Completions for installed apps
*******************************

A package can ship the completion script for its own app, the way it ships a man page. pipx *exposes* the script by
linking or copying it into the directory your shell reads, and tracks it, so the completions arrive with the package and
leave with it.

Run ``pipx list`` to see which completion scripts each environment exposes and which are missing or misplaced.

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

To ship completion scripts from your own package, see :doc:`make-packages-compatible`.
