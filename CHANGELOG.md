# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).. Please note this changelog affects 
this package and not the cluster API. See the changelog of the [cluster API](https://cluster-api.cyberfusion.nl/redoc#section/Changelog) 
for detailed information.

## [1.86.4]

### Fixed

- Properly apply nullable validation in `BorgRepository`, `DatabaseUser` and `PassengerApp` models.

## [1.86.3]

### Fixed

- Do not filter fields for the login endpoints.

## [1.86.2]

### Fixed

- Also allow nullable values when filtering fields.

## [1.86.1]

### Fixed

- Do not require `rabbitmq` for unix users as those are nullable.

## [1.86.0]

### Added

- CMS theme install endpoint.
- CMS user credentials update endpoint.

## [1.85.1]

### Fixed

- Allow the public key to be null in `getPublicKey` method.

## [1.85.0]

### Removed

- Removed `databases_data_directory` from clusters.

## [1.84.0]

### Added

- Return task collection on virtual host delete.

## [1.83.0]

### Added

- Add `certificate_id` to Domain Routers.
- Add `MailHostnames` endpoints.

## [1.82.1]

### Fixed

- Change `raw_message` to be nullable on the `AccessLog` and `ErrorLog` models, as those are turned off by default and 
  will return `null` in that case.

## [1.82.0]

### Added

- Certificate managers: `lastRequestTaskCollectionUuid` attribute.

## [1.81.0]

### Changed

- Improve the usage of the list filter. 
- There should be just one breaking change, the `SORT_*` constants of the `ListFilter` are moved to a separate Enum, 
  see `Enums\Sort`.

## [1.80.1]

### Fixed

- Fix UUID casing for task collections `results` endpoint.
- Make task result `message` nullable.

## [1.80.0]

### Changed

- Add default value for logs `timestamp`.
- Make logs `timestamp` nullable.

## [1.79.1]

### Fixed

- Rename the property `provider_names` to `provider_name` in the `CertificateManager` model.

## [1.79.0]

### Added

- Certificate managers.
- Certificates: `expiresAt` attribute.
- `UserInfo` model: `id` attribute.

### Changed

- Update to [API version 1.155](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.155-2022-11-17).
- Certificates: make certificate + CA chain + private key required and non-nullable.
- Certificates: remove `isLetsEncrypt`.
- Certificates: remove `statusMessage`.
- Logs: remove `rawMessage` regex validation.
- Logs: remove `errorMessage` regex validation.

### Fixed

- Remove `mixed` type as that requires PHP 8+.

### Removed

- Certificates: `createLetsEncryptCertificate` endpoint. This has been replaced by certificate managers.
- Certificates: `createCertificateWithOwnMaterial` endpoint. This has been replaced by the `create` endpoint.
- Remove unused import.

## [1.78.2]

### Fixed

- Change `unit_name` to be nullable.
- Fix the getters/setters of `port` to accept null value.

## [1.78.1]

### Added

- Add missing endpoint for destroying a RedisInstance.

### Fixed

- No longer require `max_databases` and `memory_limit` when creating or updating a RedisInstance.
- Make RedisInstance port nullable as it's only available after creation.
- Add default values for `max_databases` and `memory_limit`.

## [1.78.0]

### Added

- RabbitMQ encryption key attribute to UNIX users.

## [1.77.0]

### Changed

- Borg archive content symbolic mode regex has been updated.
- UNIX user RabbitMQ username + RabbitMQ password + RabbitMQ virtual host name is now required on update.
- UNIX user RabbitMQ username + RabbitMQ virtual host name regex has been updated.

## [1.76.0]

### Added

- Domain routers.

### Removed

- Balancer backend name and force SSL from URL redirects and virtual hosts. These have been replaced by domain routers.

## [1.75.1]

### Fixed

- Add `unit_name` as required field to the FPM pool update endpoint to match spec.
- Add `record_usage_files` to the unix user create endpoint to match spec.
- Add `home_directory` and `ssh_directory` to the fields and required fields for the unix user update endpoint to 
  match spec.
- Remove `domain_root` from the virtual host create endpoint to match spec.

## [1.75.0]

### Added

- UNIX users home directory usages.

## [1.74.0]

### Changed

- Use UUID instead of ID for task collection results endpoint.
- `allowOverrideOptionDirectives` and `allowOverrideDirectives` are now nullable.
- Default values for `allowOverrideOptionDirectives` and `allowOverrideDirectives` are now set based on server software.

### Fixed

- `serverSoftwareName` attribute is now sent on create and update of virtual hosts.

## [1.73.0]

### Added

- `serverSoftwareName` attribute has been added to virtual hosts.
- Values `TEMPORARY_REDIRECT` and `PERMANENT_REDIRECT` have been added to `StatusCode` Enum.

### Changed

- `objectId` and `objectModelName` attributes of task collections are now non-nullable.
- Database user password is no longer pre-hashed.
- Regex and length validations have been updated and added.
- `tokenType` attribute of login model now uses `TokenType` Enum.

### Fixed

- Added missing `password` attribute to Redis instances.

## [1.72.1]

### Fixed

- Unix user might not have a default nodejs version but validation was not allowing `null`.

## [1.72.0]

### Added

- Apply path validation on several setters.
- Add ability to validate multiple values, just call `->each()` after initializing the validator with a value.
- Pattern validation to NodeJS versions.

### Removed

- Remove `positiveInteger` validation.

## [1.71.0]

### Added

- Add the `expiresIn` attribute to tokens.
- Add the `description` attribute to clusters.

### Changed

- Update to [API version 1.143](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.143-2022-10-19).
- Add max length to `CmsInstallation` (`database_user_password` + `admin_password`) and `CmsConfigurationConstant` (`value`)
- Remove min length validation from strings.

## [1.70.0]

### Changed

- Renamed package and namespace.

## [1.69.1]

### Fixed

- Add the required `domainRoot` attribute to virtual host update payload.

## [1.69.0]

### Added

- Add the `primaryNodeId` attribute to Redis instances.

## [1.68.0]

### Added

- Add Redis instances endpoints.

## [1.67.1]

### Fixed

- Add the required `domainRoot` attribute to virtual host update payload.
- Remove the `deployCommands` attribute from virtual host, which was removed from the API earlier.

## [1.67.0]

### Added

- Add CMS regenerate salts endpoint.

## [1.66.0]

### Added

- Add CMS search & replace endpoint.

## [1.65.0]

### Added

- Add htpasswd files endpoint.
- Add htpasswd users endpoint.
- Add basic authentication realms endpoints.
- Add CMS update option endpoint.
- Add CMS update configuration constant endpoint.

## [1.64.0]

### Added

- Add virtual host sync domain root endpoint.

## [1.63.0]

### Added

- Add Borg repository archives metadata endpoint.
- Borg archive metadata now has its own model, `BorgArchiveMetadata`.

## [1.62.0]

### Added

- Add database sync endpoint.

### Changed

- Update Passenger app restart + FPM pool restart endpoints: add callback URL + return task collection model

## [1.61.0]

### Added

- Add the `objectId` attribute to task collection.
- Add the `objectModelName` attribute to task collection.

## [1.60.0]

### Added

- Add the `syncToolkitEnabled` attribute to cluster.
- Add UNIX user comparison endpoint.

## [1.59.0]

### Added

- Add the `domainRoot` attribute to virtual host.

## [1.58.0]

### Added

- Add database comparison endpoint.

### Changed

- Update docblocks.

### Removed

- Remove unused imports.
- Remove `sprintf` calls without parameters.

## [1.57.0]

### Changed

- Use `DatabaseUserGrantPrivilegeName` enum for database user grant privilege names.
- Make new `SELECT` database user grant privilege name available.
- Update to [API version 1.127](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.127-2022-06-06).

## [1.56.0]

### Changed

- Update database and database user name regex.
- Update to [API version 1.126.1](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.126.1-2022-06-02).

## [1.55.0]

### Changed

- Add support for Borg SSH key for clusters.
- Update to [API version 1.125](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.125-2022-05-27).

## [1.54.0]

### Changed

- Change validation of `startup_file` of `PassengerApp` to end with `.js`.
- Update to [API version 1.124.1](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.124.1-2022-05-21).

## [1.53.0]

### Added

- Add the `defaultNodejsVersion` attribute to UNIX user.
- Add the `cpuLimit`, `appRoot` and `isNamespaced` attributes to Passenger app.

## [1.52.0]

### Added

- Add `RootSshKeys` endpoint.

## [1.51.0]

### Added

- Add `path` to Borg archive contents, restore and download requests.

## [1.50.0]

### Added

- Add Borg archive download endpoint.

### Changed

- Fix capitalisation of Enum values of `PassengerAppTypeEnum` and `PassengerEnvironmentEnum`.
- Update to [API version 1.119](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.119-2022-04-26).

## [1.49.3]

### Fixed

- After talking to @WilliamDEdwards the task collection works a bit different then I thought. In short: a task 
  collection contains at least 2 task and always returns the results of all those tasks. Updated the endpoint to reflect
  that setup. The official documentation will be improved to provide more information about task collections and the 
  results.

## [1.49.2]

### Fixed

- Laravel 9 support failed due to using an old version of ramsey/uuid package to still support PHP 7.4. I intend to 
  support PHP 7.4 until its EOL date (28 Nov 2022) when possible.

## [1.49.1]

### Fixed

- Properly implement the task collection results.

## [1.49.0]

### Changed

- Update to [API version 1.118.3](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.118-2022-04-20).

## [1.48.1]

### Fixed

- Changed the `nodeId` property of the `Cron` model to optional.

## [1.48.0]

### Added

- Add callback url for deployments.
- Add callback url for the automatic deployments.

### Changed

- Update to [API version 1.117](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.117-2022-03-10).
- A commit will now return a task collection.

## [1.47.1]

### Fixed

- Return type of `getRecordUsageFiles` has been updated from string to bool.

## [1.47.0]

### Added

- Add the optional `recordUsageFiles` attribute to UNIX users.

### Changed

- Update to [API version 1.116](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.116-2022-03-06).

### Fixed

- Add missing attribute to create and update payload for FPM pools: `is_namespaced`
- Add missing attributes to create and update payloads for UNIX users: `shell_path`, `borg_repositories_directory`, `description`
- Add missing attributes to create and update payloads for URL redirects: `description`

## [1.46.0]

### Added

- Add the optional `timeUnit` to database, mail account, borg repository and unix user usage.

### Changed

- Update to [API version 1.115](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.115-2022-03-04).
- Renamed `from_timestamp_date` parameter to `timestamp`. This does not affect the usage of the package.

## [1.45.0]

### Added

- Add `TaskCollection` endpoint.
- Add `callbackUrl` to cms install and fpm reload requests.

### Changed

- Update to API version 1.110.
- The cms install and fpm reload request now return a `TaskCollection`.

## [1.44.0]

### Added

- Add support for Laravel 9.

### Changed

- Isolated Laravel helper.

## [1.43.1]

### Fixed

- The cron `toArray` used `setRandomDelayMaxSeconds` instead of `getRandomDelayMaxSeconds`.
 
## [1.43.0]

### Added

- Add nodes endpoint.
- Add `random_delay_max_seconds` attribute to the `Cron` model.

## [1.42.0]

### Added

- Add `node_id` attribute to the `Cron` model.

## [1.41.0]

### Added

- Add the ability to reload an FPM pool.

## [1.40.0]

### Changed

- Full rework of the validation logic in the models including tests.

## [1.39.1]

### Changed

- Update to [API version 1.106.2](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.106.2-2022-01-24).
- Update regex for mail account and mail alias local part

## [1.39.0]

### Added

- Add `log_slow_requests_threshold` attribute to the `FpmPool` model.
- Add `createPublic` and `createPrivate` methods to the `SshKeys` endpoint for creating a public or private SSH key.
- Add several validations for several attributes.
- Add `sort` attribute to the `LogFilter`.

### Changed

- Update to [API version 1.106](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.106-2022-01-21).
- Moved the sort and limit constants to their own enums.

## [1.38.2]

### Fixed

- Make sure the `allow_override_directives` and `allow_override_option_directives` are in the request body of the 
 `VirtualHost`. 

## [1.38.1]

### Fixed

- Replace 300 by 303 in `StatusCode`

## [1.38.0]

### Added

- Add `description` to the `UrlRedirect` model.

### Changed

- Update to [API version 1.105.0](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.105-2021-12-28).

### Removed

- Remove the `update` method from the `Certificate` endpoint.

## [1.37.0]

### Added

- Add URL redirects endpoint.

### Changed

- Update to [API version 1.104.1](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.104.1-2021-12-20).

## [1.36.0]

### Changed

- Update to [API version 1.103](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.103-2021-12-16).

### Fixed

- Use the proper snake_case fields when using the ListFilter.

### Removed

- Remove the database user grant delete endpoint as it's no longer available.

## [1.35.0]

### Added

- Add the `is_lets_encrypt` property to the `Certificate` model.

### Changed

- Update to [API version 1.102](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.102-2021-12-15).

## [1.34.0]

### Added

- Add the Let's Encrypt certificate endpoint: `createLetsEncryptCertificate`.
- Add the endpoint to provide your own SSL certificates: `createCertificateWithOwnMaterial`.

### Changed

- Update to [API version 1.101](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.101-2021-12-14).
- Issue templates to assign the correct user instead of the organisation. Also made the bug report a bit easier to use.

### Fixed

- Not all headers in this changelog were of the correct depth.

### Removed

- Remove the `common_names` and `main_common_name` from the certificate update as it can't be changed.
- Remove the SSH key update endpoint as it's no longer available.

## [1.33.1]

### Fixed

- The MariaDB password hash for Database Users is now generated correctly.

### [1.33.0]

## Changed

- Update to [API version 1.97](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.97-2021-12-02).
- Always send the hashed password for the Database User but be able to set the hashed password with `setHashedPassword`
  or plain text password with `setPassword`. Thanks to @mbardelmeijer.
- Setting the Database Engine of the Database User after setting the password will result in a `ModelException` as the
  password hash is based on the engine.

## [1.32.2]

### Fixed

- Make e-mailaddress of the Cron and the unit name of the FPM pool optional.

## [1.32.1]

### Fixed

- Use reflection instead of toArray to determine the available fields to prevent accessing fields which aren't 
  initialized.

## [1.32.0]

### Changed

- Improve the ListFilter.
- Add documentation about the filter.
- Throw exception when filtered on a field which doesn't belong to the model.

## [1.31.0]

### Changed

- Removed Psalm in favor of PHPStan.

## [1.30.1]

### Fixed

- Fix the type of the unix name in the FPMPool model. Thanks to @szepeviktor.

## [1.30.0]

### Added

- Add `oneTimeLogin` endpoint for CMS.
- Add `documentRootFiles` endpoint for Virtual Hosts.

### Changed

- Restored the ability to track cluster deployments when installing a CMS and still returns the CMS object (required 
  because the cluster API no longer returns the CMS object).
- The FPM pool restart endpoint no longer returns the FPM pool object (as the cluster API no longer returns the FPM pool
  object).
- Update to [API version 1.88](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.88-2021-11-09).
- The `ListFilter` can now be initialized for models which enables checks for available fields to filter or sort on.

### Fixed

- Properly encode timestamps in usage endpoints.

### Removed

- Remove `$oneTimeLogin` parameter from CMS get endpoint in favor of the `oneTimeLogin` endpoint.
- Remove `$documentRootContainsFiles` parameter from VirtualHost get endpoint in favor of the `documentRootFiles` 
  endpoint instead.

## [1.29.1]

### Fixed

- After an FPM pool restart, there's no need to deploy the cluster.

## [1.29.0]

### Added

- Add `disableAsync` to the `UnixUsers` endpoint. Thanks to @WilliamDEdwards.
- Add `unit name` property to the FPM pool. Thanks to @WilliamDEdwards.
- Add version based user agent, i.e. `cyberfusion-cluster-api-client/1.29`. Thanks to @WilliamDEdwards. 

### Changed

- Add positive integer validation to `keep_hourly`, `keep_daily`, `keep_weekly`, `keep_monthly`, `keep_yearly` of Borg 
  Repositories.
- Add positive integer validation to `error_count` of Crons.
- Add positive integer validation to `max_children`, `max_requests`, `process_idle_timeout` and `cpu_limit` of FPM 
  pools.
- Add positive integer validation to `quota` of Mail accounts.
- Update to [API version 1.77](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.77-2021-09-30)

## [1.28.0]

### Added

- Add the ability to restart a FPM pool. Thanks to @Arne-Jan.

## [1.27.0]

### Changed

- The `from_timestamp_date` parameter is now required for Borg Repository Usages, Database Usages, Mail Account Usages 
  and Unix User Usages.
- Update to [API version 1.65](https://cluster-api.cyberfusion.nl/redoc#section/Changelog/1.65-2021-09-02)

## [1.26.0]

### Added

- Add `description` to unix user.
- Add `borg_repositories_directory` to unix user.
- Add user agent for this client, see `USER_AGENT` in `Client`.

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
- Add commit call to the cluster endpoint. See the [readme](README.md) for more information.

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
