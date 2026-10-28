Stop ``pipx reinstall`` from replacing the main package while it replays injected packages. The replay passed
``--force-reinstall``, so an injected package that depends on the main package made the installer fetch the main
package again by name from the injected package's index and install that release over the recorded source.
