# Contributing

Contributions are **welcome** and you will be credited as a contributor.

The goal of this package is to enable developers to easily use the Core API of Cyberfusion. To make sure this
package is focused on that goal, there are some guidelines defined. Please read this contribution guide **before**
creating an issue or pull request.

## We are all humans

This project is an open-source package and targets the users of the Cyberfusion Core API. This package isn't
maintained by Cyberfusion, but is built and maintained in the maintainer's (and contributor's) spare time.

Please be considerate towards everyone who's involved with the package, when raising issues or creating pull requests.
Let's make this repository a friendly and welcoming place with honest feedback and respect for each other.

## Benefit to the goal

When requesting or submitting features/changes, consider whether it benefits the goal. Determine if most of the users
benefit from the feature and/or change.

It's the task of the maintainer to make sure that all additions or changes to the project benefit its goal. That could
mean your addition or change won't be merged. To prevent you wasting your valuable time on such a thing, feel free to
open an issue or discussing in front.

## Procedure

Before creating an issue:

- Try to replicate the problem with the smallest usage possible.
- When creating a feature request, make sure the feature isn't present already.
- Make sure there's not yet another issue or a pull request available about the same feature/change.

Before submitting a pull request:

- Make sure the feature/change isn't present already.
- Make sure there's not yet another issue or a pull request available about the same feature/change.

The maintainer will look at your issue and pull requests as soon as possible. There's no need to mention and/or contact
the maintainer about your issue or pull request as the maintainer will be notified by GitHub.

Feel free to tag the maintainer when you didn't get a response in one week.

## Breaking changes

Be aware this package is implemented by other developers. By introducing breaking changes, those developers need to
update their implementation too. For that reason, try to make as few as possible breaking changes.

## Versioning

The versioning follows [SemVer](http://semver.org/). In short:

- Increase the MAJOR version when you make incompatible API changes,
- Increase the MINOR version when you add functionality in a backwards compatible manner,
- Increase PATCH version when you make backwards compatible bug fixes.

## Requirements

There are some requirements set by the maintainer, which are listed below.

- Please apply the [PSR-12 Coding Standard](https://github.com/php-fig/fig-standards/blob/master/accepted/PSR-12-coding-style-guide.md).
- Keep track of changes and document them in the [CHANGELOG.md](CHANGELOG.md).
- Update the [readme.md](README.md) when the Core API version is updated.
- Add tests when possible.
- Please create one pull request per feature/bug.
