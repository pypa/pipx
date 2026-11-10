``pipx uninject`` also removes the dependencies of the dependencies it removes, so uninjecting a package that needs
``scipy`` no longer leaves ``numpy`` behind.
