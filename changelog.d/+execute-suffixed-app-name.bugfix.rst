``pipx execute`` accepts an app by the suffixed name it has on ``PATH`` when its environment was installed with
``--suffix`` or its package was injected with ``--with-suffix``, including names that pipx 1.17.14 and earlier
exposed with the suffix before the last dot, such as ``pip3@1.12``.
