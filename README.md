# Cyberfusion Core API client

Client for the [Cyberfusion Core API](https://core-api.cyberfusion.io/).

This client was built for and tested on the **1.230.1** version of the API.

## Support

This client is officially supported by Cyberfusion. If you have any questions, open an issue on GitHub or email 
support@cyberfusion.nl.

The client was created by @dvdheiden.

## Requirements

This client requires PHP 8.1 or higher and uses Guzzle.

## Installation

This client can be used in any PHP project and with any framework.

Install the client with Composer:

`composer require cyberfusion/cluster-api-client`

## Usage

Refer to the [API documentation](https://core-api.cyberfusion.io/) for information about API requests.

### Getting started

```php
use Cyberfusion\ClusterApi\Client;
use Cyberfusion\ClusterApi\Configuration;
use Cyberfusion\ClusterApi\ClusterApi;

// Create the configuration with your username/password
$configuration = Configuration::withCredentials('username', 'password');

// Start the client once and authorize
$client = new Client($configuration);

// Initialize the API
$api = new ClusterApi($client);

// Perform the request
$result = $api->virtualHosts()->list();

// Access the virtual host models
$virtualHosts = $result->getData('virtualHosts');
```

### Requests

The endpoint methods may ask for filters, models and IDs. The method type hints tell you which input is requested.

#### Models

The endpoint may request a model. Most create and update requests do.

```php
$unixUserUsername = 'foo';

$unixUser = (new UnixUser())
    ->setUsername($unixUserUsername)
    ->setPassword('bar')
    ->setDefaultPhpVersion('7.4')
    ->setVirtualHostsDirectory(sprintf('/home/%d', $unixUserUsername))
    ->setClusterId(1);

$result = $api
    ->unixUsers()
    ->create($unixUser);
```

When models need to be provided, the required properties are checked before executing the request.

`RequestException` is thrown when properties are missing. See the error message for more details.

#### Filtering data

Some endpoints require a `ListFilter` and return a list of models according to the filter. It's also possible to change 
the sort order.

##### Model filters

A `ListFilter` can be initialized for a model, so it automatically validates if the provided fields are available for 
the model.

```php
use Cyberfusion\ClusterApi\Enums\Sort;
use Cyberfusion\ClusterApi\Models\VirtualHost;
use Cyberfusion\ClusterApi\Support\FilterEntry;
use Cyberfusion\ClusterApi\Support\SortEntry;

$listFilter = VirtualHost::listFilter()
    ->filter(new FilterEntry('server_software_name', 'Apache'))
    ->filter(new FilterEntry('domain', 'cyberfusion.nl'))
    ->sort(new SortEntry('domain', Sort::DESC));
```

##### Manually creating filters

You can initialize the `ListFilter` manually, but fields are not validated if they are available for the model.

```php
$listFilter = (new ListFilter())
    ->filter(new FilterEntry('server_software_name', 'Apache'))
    ->filter(new FilterEntry('domain', 'cyberfusion.nl'))
    ->sort(new SortEntry('domain', Sort::DESC));
```

Or provide the entries and sort directly:

```php
$listFilter = (new ListFilter())
    ->setFilters([
        new FilterEntry('server_software_name', 'Apache'),
        new FilterEntry('domain', 'cyberfusion.nl'),
    ])
    ->setSort([
        new SortEntry('domain', Sort::DESC)
    ]);
);
```

##### Alternative method

This package used to offer this way to build the filter. Due to backwards compatibility, this functionality is still 
available.

```php
$listFilter = ListFilter::forModel(new Cluster())
    ->filter('server_software_name', 'Apache')
    ->filter('domain', 'cyberfusion.nl')
    ->sort('domain', Sort::DESC);
```

Or provide the entries and sort directly:

```php
$listFilter = (new ListFilter())
    ->setFilters([
        ['field' => 'server_software_name', 'value' => 'Apache'],
        ['field' => 'domain', 'value' => 'cyberfusion.nl'],
    ])
    ->setSort([
        ['field' => 'domain', 'value' => Sort::DESC],
    ]);
);
```

#### Manually make requests

To use the API directly, use the `request()` method on the `Client`. This method needs a `Request` class. See the class 
itself for its options.

### Responses

The endpoint methods throw exceptions when requests fail due to timeouts. When the API replies with HTTP protocol 
errors, the `Response` class is returned nonetheless. Check if the request succeeded with: `$response->isSuccess()`. 
API responses are automatically converted to models.

### Authentication

The API is authenticated with a username and password and returns an access token. This client takes care of 
authentication. To get credentials, contact Cyberfusion.

```php
$configuration = Configuration::withCredentials('username', 'password');
```

When you authenticate with username and password, this client automatically retrieves the access token.

The access token is valid for 30 minutes, so there's no need to store it. To store it anyway, access it with 
`$configuration->getAccessToken()`.

#### Manually authenticate

```php
use Cyberfusion\ClusterApi\Client;
use Cyberfusion\ClusterApi\ClusterApi;
use Cyberfusion\ClusterApi\Configuration;
use Cyberfusion\ClusterApi\Models\Login;

// Initialize the configuration without any credentials or access token
$configuration = new Configuration();

// Start the client with manual authentication
$client = new Client($configuration, true);

// Initialize the API
$api = new ClusterApi($client);

// Create the request
$login = (new Login())
    ->setUsername('username')
    ->setPassword('password');

// Perform the request
$response = $api
    ->authentication()
    ->login($login);

// Store the access token in the configuration
if ($response->isSuccess()) {
    $configuration->setAccessToken($response->getData('access_token'));
}
```

### Enums

Some properties should contain certain values. These values can be found in the enum classes.

### Exceptions

In case of errors, the client throws an exception which extends `ClusterApiException`.

All exceptions have a code. These can be found in the `ClusterApiException` class.

### Laravel

This client can be easily used in any Laravel application. Add your API credentials to the `.env` file:

```
CLUSTER_USERNAME=username
CLUSTER_PASSWORD=password
```

Next, create a config file called `cluster.php` in the `config` directory:

```php
<?php

return [
    'username' => env('CLUSTER_USERNAME'),
    'password' => env('CLUSTER_PASSWORD'),
];
```

Use those files to build the configuration:

```php
$configuration = Configuration::withCredentials(config('cluster.username'), config('cluster.password'));
```

## Tests

Unit tests are available in the `tests` directory. Run:

`composer test`

To generate a code coverage report in the `build/report` directory, run:

`composer test-coverage`

## Contribution

Contributions are welcome. See the [contributing guidelines](CONTRIBUTING.md).

## Security

If you discover any security related issues, please email support@cyberfusion.nl instead of using the issue tracker.

## License

This client is open-sourced software licensed under the [MIT license](http://opensource.org/licenses/MIT).
