``pipx upgrade-all --pip-args=--index-url``, or any other index option given without a value, now fails with an error
naming the option instead of a ``StopIteration`` traceback, and ``--output json`` reports it in the usual error
envelope.
