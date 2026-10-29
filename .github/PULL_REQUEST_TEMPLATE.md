### Thanks for contributing! Work through this checklist before review (the [development documentation](https://pipx.pypa.io/latest/contributing.html) explains how)

- [ ] ran the repository checks (`prek run --all-files`)

- [ ] wrote descriptive pull request text

- [ ] ensured there are test(s) validating the fix

- [ ] added a `changelog.d/+topic.type.rst` fragment for a user-facing change, or applied `skip news` for maintenance
    work

- [ ] updated/extended the documentation

- [ ] ran tests on Python 3.11 and 3.15 (`tox run -e 3.11,3.15`)

- [ ] linked upstream issues beside any temporary interpreter overrides

- [ ] kept the PR in draft until CI passes
