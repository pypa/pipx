# Cyberfusion cluster API client

Easily use the [API of the clusters](https://cluster-api.cyberfusion.nl/) of the hosting company 
[Cyberfusion](https://cyberfusion.nl/). This package is build and tested on the **1.77** version of the API.
This package is not created or maintained by Cyberfusion.

## Requirements

This package requires PHP 7.4 and uses Guzzle.

## Installation

This package can be used in any PHP project or with any framework.

You can install the package via composer:

`composer require vdhicts/cyberfusion-cluster-api-client`

## Usage

This package is just an easy client for using the Cyberfusion Cluster API. Please refer to the 
[API documentation](https://cluster-api.cyberfusion.nl/) for more information about the requests.

### Getting started

```php
use Vdhicts\Cyberfusion\ClusterApi\Client;
use Vdhicts\Cyberfusion\ClusterApi\Configuration;
use Vdhicts\Cyberfusion\ClusterApi\ClusterApi;

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

### Sandbox mode

To easily test your implementation, you can enable the sandbox mode. Changes won't be made to your cluster.

To enable the sandbox mode, use the third parameter of the configuration, or set it separately:

```php
$configuration = Configuration::withCredentials('username', 'password', true);
```

Or

```php
$configuration = (new Configuration())
    ->setUsername('username')
    ->setPassword('password')
    ->setSandbox(true);
```

### Requests

The endpoint methods may ask for filters, models or id's. The method typehints will tell you which input is requested.

#### Models

The endpoint may request a model, most create and update requests do. 

```php
$unixUser = (new UnixUser())
    ->setUsername('foo')
    ->setPassword('bar')
    ->setDefaultPhpVersion('7.4')
    ->setClusterId(1);

$result = $api
    ->unixUsers
    ->create($unixUser);
```

When models need to be provided, the required properties will be checked before executing the request. A 
`RequestException` will be thrown when properties are missing. See the message for more details.

#### Manually make requests

When you want to use the API directly, you can use the `request()` method on the `Client`. This method needs a `Request`
class. See the class itself for its options.

#### Committing changes

A commit is required when you perform a create/update/delete for:

- mail aliases 
- mail accounts
- mail domains
- ssh keys
- unix users
- fpm pools
- crons
- virtual hosts
  
**_You **MUST** commit the changes for each cluster as this is required to update the cluster!_**

```php
$api
    ->clusters()
    ->commit($clusterId);
```

### Responses

The endpoint methods throw exceptions when the request fails due to timeouts. When the API replies with HTTP protocol 
errors the `Response` class is still returned. You can check the success of the request with: `$response->isSuccess()`. 
The content of the response is automatically converted to the models.

### Authentication

The API is authenticated with a username and password and returns an access token. This package takes care of the
authentication for you. To get your credentials, you need to contact Cyberfusion.

```php
$configuration = Configuration::withCredentials('username', 'password');
```

When you authenticate with username and password, this package will automatically retrieve the access token. The access 
token is valid for 30 minutes, so there's not really any need to store this. If you want to store the access token 
anyway, it's stored in the `Configuration` class and accessible with: `$configuration->getAccessToken()`.

#### Manually authenticate

It's also an option to manually authenticate:

```php
use Vdhicts\Cyberfusion\ClusterApi\Client;
use Vdhicts\Cyberfusion\ClusterApi\ClusterApi;
use Vdhicts\Cyberfusion\ClusterApi\Configuration;
use Vdhicts\Cyberfusion\ClusterApi\Models\Login;

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

Some models have properties that should contain certain values. These values can be found in the enum classes and are 
there just for reference.

### Exceptions

When something goes wrong, the client will throw an exception which extends the `ClusterApiException`. If you want to 
catch exceptions from this package, that's the one you should catch. All exceptions have a code, these codes can be 
found in the `ClusterApiException` class.

### Deployment

Change to most of the objects in the cluster API require a deployment of the cluster. See [Cluster Deployment](https://cluster-api.cyberfusion.nl/redoc#operation/create_cluster_deployment_api_v1_cluster_deployments_post) for more information.

This package keeps track of the affected clusters. The `deploy` method on the client will automatically deploy all 
affected clusters for you:

```php
$clusterDeployments = $client->deploy();
```

The result will be an array of `Deployment` objects (or an empty array who no clusters are affected) which enables you 
to check if the cluster is properly deployed:

```php
foreach ($clusterDeployments as $clusterDeployment) {
    $success = $clusterDeployment->isSuccess();
    if (!$success) {
        // Do something with $clusterDeployment->getError();
    }
}
```

See the `Deployment` class for more options.

#### Automatic deployment

To make life easy, this package is also able to deploy any affected cluster automatically. This is opt-in behavior as 
you won't be able to access the result of the deployment. Enable this behavior in the configuration:

```php
$configuration = new Configuration();
$configuration->setAutoDeploy(); // Enable the auto deployment of affected clusters

// Initialize the client
$client = new Client($configuration, true);

// Initialize the API
$api = new ClusterApi($client);
```

### Laravel

This package can be easily used in any Laravel application. I would suggest adding your username and password to your 
`.env` file:

```
CLUSTER_USERNAME=username
CLUSTER_PASSWORD=password
```

Next create a config file `cluster.php` in `/config`:

```php
<?php

return [
    'username' => env('CLUSTER_USERNAME'),
    'password' => env('CLUSTER_PASSWORD'),
];
```

And use those files to build the configuration:

```php
$configuration = Configuration::withCredentials(config('cluster.username'), config('cluster.password'));
```

In the future I might make a Laravel specific package which uses this package.

## Tests

Unit tests are available in the `tests` folder. Run with:

`composer test`

When you want a code coverage report which will be generated in the `build/report` folder. Run with:

`composer test-coverage`

## Contribution

Any contribution is welcome, but it should meet the PSR-2 standard and please create one pull request per feature/bug. 
In exchange, you will be credited as contributor on this page.

## Security

If you discover any security related issues in this or other packages of Vdhicts, please email info@vdhicts.nl instead
of using the issue tracker.

## Support

This package isn't an official package from Cyberfusion, so they probably won't offer support for it. If you encounter a
problem with this client or has a question about it, feel free to open an issue on GitHub.

## License

This package is open-sourced software licensed under the [MIT license](http://opensource.org/licenses/MIT).

## About Vdhicts

[Vdhicts](https://www.vdhicts.nl) is the name of my personal company for which I work as freelancer. Vdhicts develops 
and implements IT solutions for businesses and educational institutions.
