# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to 
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Please note this changelog affects this package and not the 
cluster API. See the changelog of the [cluster API](https://cluster-api.cyberfusion.nl/redoc#section/Changelog) for 
detailed information.

## [1.27.0]

### Changed

- The `from_timestamp_date` parameter is now required for Borg Repository Usages, Database Usages, Mail Account Usages 
  and Unix User Usages.
- Update to [API version 1.65](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.65-2021-09-02)

## [1.26.0]

### Added

- Add `description` to unix user.
- Add `borg_repositories_directory` to unix user.

### Changed

- Change `process_idle_timeout` to `10`.

### Removed

- Remove commands endpoint and model.
- Remove `command_toolkit_enabled` from cluster.

## [1.25.0]

### Added

- Add `bubblewrap_toolkit_enabled` to cluster.
- Add `main_common_name` to certificate.

## [1.24.2]

### Fixed

- The CMS model required fields which might not be present when creating a CMS.

## [1.24.1]

### Fixed

- The list filter now works properly and works with multiple filter arguments.

## [1.24.0]

### Added

- Add create, delete and install methods to the CMS endpoint. 
- Add `is_active` property to crons. 
- Add async support to UnixUsers.
- Add the max limit to list requests.

### Changed

- Change the email address to be optional for crons. 
- Update to [API version 1.56](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.56-2021-07-13)

## [1.23.1]

### Fixed

- Change the databases usages endpoint which now correctly handles empty usage. Thanks to @Arne-Jan.

## [1.23.0]

### Changed

- Requesting a Let's Encrypt certificate not longer requires a cluster deployment.
- Update to [API version 1.48](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.48-2021-06-17)

### Fixed

- Change the `Str::match` to `Str::doesMatch` to not conflict with new Laravel helper.

## [1.22.0]

### Added

- Add regex validation to the name of a database user.
- Add `locking_enabled` property to crons.

### Changed

- Change regex validation to allow capticals for the `table_name` of a database user grant.
- Update to [API version 1.47](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.47-2021-06-04)

## [1.21.2]

### Changed

- Add default of empty string to setName in Cluster model's fromArray

## Fixed

- Fix error with deployment due to affected clusters not being initialized.
- Fix error with the document root files being `null` when no files are present but an array is expected.

## [1.21.1]

### Changed

- Improve the contract for the client to support the deployment.

## [1.20.0]

### Added

- Add (auto) deployment of affected clusters. See the [README.md](README.md) for more information about the usage of 
  deployments. 

## [1.19.0]

### Added

- Add `get_document_root_contains_files` parameter to the `get` method on VirtualHost.

## [1.18.0]

### Added

- Borg repository usages and update endpoint.
- Borg archives get endpoint.
- Add the `BORG_SERVER` cluster group.
- Add `private_key` property to SSH keys.
- Add malware toolkit fields to Cluster.
- Add `unix_user_id` property to Malware.

### Changed

- Renamed `BORG` cluster group to `BORG_CLIENT` to match the spec.
- Retention fields of a borg repository are now nullable.
- Renamed `name` attribute of a CMS to `software_name` to match the spec.

### Removed

- Removed the `virtual_host_id` property from malware.

## [1.17.1]

### Fixed

- Fix empty string for all tables on database grants.

## [1.17.0]

### Added

- Add Borg Repositories endpoint.

### Changed

- Update to [API version 1.35.1](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.35.1-2021-04-28)

## [1.16.0]

### Added

- Add `command_toolkit_enabled` attribute to Clusters.

### Changed

- Update to [API version 1.34](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.34-2021-04-23)

### Removed

- The `nologin` shell path is no longer available.

## [1.15.1]

### Fixed

- Change the required fields to match the latest spec.

## [1.15.0]

### Added

- Add jsonSerializable support to the models. This allows you to `json_encode` the models.

## [1.14.1]

### Fixed

- Fix pattern validation on models.

## [1.14.0]

### Added

- Add `is_namespaced` attribute to FPM pools.
- Add `shell_path` enum attribute to Unix Users.

### Changed

- Update to [API version 1.32](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.32-2021-04-10)

## [1.13.0]

### Changed

- Update to [API version 1.29.1](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.29.1-2021-04-07)

## [1.12.0]

### Added

- Add support for one time login url for cmses.

## [1.11.0]

### Added

- Add several attributes to clusters.
- Add validation to several properties.

### Changed

- Update to [API version 1.28](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.28-2021-03-29)
- Change to getters and setters for the properties to allow validation of the properties. To prevent breaking 
  implementations, property access is still available but the use of the getters and setters is recommended.

## [1.10.0]

### Added

- Add crud for databases.
- Add crud for database users.
- Add crud for database user grants.

### Changed

- Update to [API version 1.22](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.22-2021-03-23)

## [1.9.0]

### Added

- Add `host` attribute to database users.
- Add endpoint for retrieving the malware of a virtual host.

### Changed

- Update to [API version 1.21](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.21-2021-03-18)

## [1.8.1]

### Changed

- Fix issue with cluster deployments (#19)

## [1.8.0]

### Added

- Add `from` parameter to unix user, database and mail accounts usages.
- Add mail domains update method.
- Add mail domains `is_local` property.

### Changed

- Update to [API version 1.19](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.19-2021-03-12)

## [1.7.0]

### Added

- Add commands endpoint which were added in [API version 1.16](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.16-2021-03-05).

### Changed

- Update to [API version 1.17](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.17-2021-03-08)

## [1.6.2]

### Fixed

- Fix the parsing of the unix user usage response, which could be an empty array of multiple objects.

## [1.6.1]

### Fixed

- Fix general validation check to not mark a boolean with `false` or an empty array as invalid.
- Fix validation field for FPM pool endpoint

## [1.6.0]

### Added

- Add database users endpoint.
- Add mail aliases endpoint.
- Add `balancer_backend_name` to virtualhosts.
- Add `catch_all_forward_email_addresses` to mail domain.
- Add commit call to the cluster endpoint. See the [readme](readme.md) for more information.

### Changed

- Update to [API version 1.12](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.12-2021-02-23)

### Removed

- Remove `forward_email_addresses` from mail accounts.

## [1.5.0]

### Added

- Add directory fields to the unix user.

### Fixed  

- Properly handle HTTP 500 errors.

## [1.4.3]

### Fixed

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
