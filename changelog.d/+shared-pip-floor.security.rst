Require pip 26.2.2 or later in the shared libraries, and replace an older shared pip on the next pipx command instead of
waiting for the 30-day refresh. Older pip releases bundle a certifi that still trusts the compromised eMudhra/emSign root
CA.
