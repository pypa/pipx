from setuptools import setup

setup(
    name="repeatme",
    version=0.1,
    description="Repeat arguments.",
    packages=["repeatme"],
    extras_require={"cow": ["pycowsay==0.0.0.2"]},
    entry_points={"console_scripts": ["repeatme=repeatme.main:main"]},
)
