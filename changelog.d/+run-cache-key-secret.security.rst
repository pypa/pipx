``pipx run`` now names its cached environments with an HMAC keyed by a random per-user secret, stored with mode
``0600`` in ``.run-key`` inside the run cache. Before, the name was a plain hash of inputs that include tokens and
proxy passwords from the environment, so another account that could list the cache could check guesses at those
values against it. Existing cache entries are not reused and expire as usual.
