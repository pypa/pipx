``pipx run --with`` now installs the ``--with`` packages in the same installer call as the app. A ``--with`` naming a
package the app already depends on, such as ``--with 'dep==1.0'``, was skipped as already installed, so the app ran
with the newest release on the pip backend. A ``--with`` naming the app with an extra no longer links the cached
environment's commands into ``PIPX_BIN_DIR``.
