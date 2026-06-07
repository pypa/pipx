from setuptools import setup

setup(
    name="local-manpage",
    version="0.1",
    packages=["local_manpage"],
    entry_points={"console_scripts": ["local-manpage=local_manpage.main:main"]},
    data_files=[("share/man/man1", ["man/local-manpage.1"])],
)
