from setuptools import setup

setup(
    name="local-completion",
    version="0.1",
    packages=["local_completion"],
    entry_points={"console_scripts": ["local-completion=local_completion.main:main"]},
    data_files=[
        ("share/bash-completion/completions", ["completions/local-completion"]),
        ("share/zsh/site-functions", ["completions/_local-completion"]),
        ("share/fish/vendor_completions.d", ["completions/local-completion.fish"]),
    ],
)
