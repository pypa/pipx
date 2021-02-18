# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to 
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.3]

- Fix several issues with the mixed body schemas.

## [1.4.0]

### Changed

- Update to [API version 1.9](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.9-2021-02-01).

## [1.3.0]

### Changed

- Update to [API version 1.7](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.7-2021-01-27).

## [1.2.0]

### Added

- When the client is initialized, the availability of the API is checked. An exception will be thrown when the API isn't 
  available.

## [1.1.0]

### Added

- Add sandbox mode. Enable the sandbox mode in the configuration class, see the readme for more information.
- Add the `databases` endpoint, which allows you to list and get databases and view the disk usage.
- Add the `data_directory` attribute to the cluster model.
- Add psalm as static analysis tool.

## [1.0.0]

### Added

- Add the initial cluster API implementation.
