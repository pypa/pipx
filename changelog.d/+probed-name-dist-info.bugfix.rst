Refuse a URL spec whose installed ``METADATA`` names a different project than its ``.dist-info`` directory. A wheel
could rewrite that name through its data files and make ``pipx install --upgrade URL`` install it into another
application's environment.
