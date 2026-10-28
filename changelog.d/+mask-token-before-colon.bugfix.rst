Mask the user part of URL credentials that contain a colon, so a token written as ``https://TOKEN:@host`` or
``TOKEN:x-oauth-basic@`` no longer shows in the command log, ``--verbose`` output and messages. Such URLs now show as
``****:****@``, which also hides a plain user name such as ``alice``.
