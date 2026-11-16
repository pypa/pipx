``pipx uninject`` also removes the dependencies of the dependencies it removes, including ones that require each
other, so uninjecting a package that needs ``scipy`` no longer leaves ``numpy`` behind.
