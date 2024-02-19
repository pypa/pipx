<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Enums\TimeUnit;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Cluster;
use Cyberfusion\ClusterApi\Models\ClusterCommonProperties;
use Cyberfusion\ClusterApi\Models\HostIpAddress;
use Cyberfusion\ClusterApi\Models\IpAddressCreate;
use Cyberfusion\ClusterApi\Models\IpAddressProduct;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Models\UnixUsersHomeDirectoryUsage;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use DateTimeInterface;

class Clusters extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if ($filter === null) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('clusters?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'clusters' => array_map(
                fn (array $data) => (new Cluster())->fromArray($data),
                $response->getData()
            ),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function get(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('clusters/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cluster' => (new Cluster())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(Cluster $cluster): Response
    {
        $this->validateRequired($cluster, 'create', [
            'groups',
            'unix_users_home_directory',
            'php_versions',
            'mariadb_version',
            'mariadb_cluster_name',
            'php_settings',
            'http_retry_properties',
            'custom_php_modules_names',
            'php_ioncube_enabled',
            'kernelcare_license_key',
            'redis_password',
            'redis_memory_limit',
            'nodejs_versions',
            'nodejs_version',
            'customer_id',
            'wordpress_toolkit_enabled',
            'database_toolkit_enabled',
            'mariadb_backup_interval',
            'mariadb_backup_local_retention',
            'postgresql_version',
            'postgresql_backup_interval',
            'postgresql_backup_local_retention',
            'malware_toolkit_enabled',
            'malware_toolkit_scans_enabled',
            'mariadb_toolkit_enabled',
            'mariadb_toolkit_scans_enabled',
            'bubblewrap_toolkit_enabled',
            'sync_toolkit_enabled',
            'automatic_borg_repositories_prune_enabled',
            'php_sessions_spread_enabled',
            'description',
            'new_relic_apm_license_key',
            'new_relic_infrastructure_license_key',
            'new_relic_mariadb_password',
            'meilisearch_master_key',
            'meilisearch_environment',
            'meilisearch_backup_interval',
            'meilisearch_backup_local_retention',
            'automatic_upgrades_enabled',
            'firewall_rules_external_providers_enabled',
            'site_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('clusters')
            ->setBody(
                $this->filterFields($cluster->toArray(), [
                    'groups',
                    'unix_users_home_directory',
                    'php_versions',
                    'mariadb_version',
                    'mariadb_cluster_name',
                    'php_settings',
                    'http_retry_properties',
                    'custom_php_modules_names',
                    'php_ioncube_enabled',
                    'kernelcare_license_key',
                    'redis_password',
                    'redis_memory_limit',
                    'nodejs_versions',
                    'nodejs_version',
                    'customer_id',
                    'wordpress_toolkit_enabled',
                    'database_toolkit_enabled',
                    'mariadb_backup_interval',
                    'mariadb_backup_local_retention',
                    'postgresql_version',
                    'postgresql_backup_interval',
                    'postgresql_backup_local_retention',
                    'malware_toolkit_enabled',
                    'malware_toolkit_scans_enabled',
                    'mariadb_toolkit_enabled',
                    'mariadb_toolkit_scans_enabled',
                    'bubblewrap_toolkit_enabled',
                    'sync_toolkit_enabled',
                    'automatic_borg_repositories_prune_enabled',
                    'php_sessions_spread_enabled',
                    'description',
                    'new_relic_apm_license_key',
                    'new_relic_infrastructure_license_key',
                    'new_relic_mariadb_password',
                    'meilisearch_master_key',
                    'meilisearch_environment',
                    'meilisearch_backup_interval',
                    'meilisearch_backup_local_retention',
                    'automatic_upgrades_enabled',
                    'firewall_rules_external_providers_enabled',
                    'site_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cluster' => (new Cluster())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(Cluster $cluster): Response
    {
        $this->validateRequired($cluster, 'update', [
            'name',
            'groups',
            'unix_users_home_directory',
            'php_versions',
            'mariadb_version',
            'mariadb_cluster_name',
            'php_settings',
            'http_retry_properties',
            'custom_php_modules_names',
            'php_ioncube_enabled',
            'kernelcare_license_key',
            'redis_password',
            'redis_memory_limit',
            'nodejs_versions',
            'nodejs_version',
            'customer_id',
            'wordpress_toolkit_enabled',
            'database_toolkit_enabled',
            'mariadb_backup_interval',
            'mariadb_backup_local_retention',
            'postgresql_version',
            'postgresql_backup_interval',
            'postgresql_backup_local_retention',
            'malware_toolkit_enabled',
            'malware_toolkit_scans_enabled',
            'mariadb_toolkit_enabled',
            'mariadb_toolkit_scans_enabled',
            'bubblewrap_toolkit_enabled',
            'sync_toolkit_enabled',
            'automatic_borg_repositories_prune_enabled',
            'php_sessions_spread_enabled',
            'description',
            'new_relic_apm_license_key',
            'new_relic_infrastructure_license_key',
            'new_relic_mariadb_password',
            'meilisearch_master_key',
            'meilisearch_environment',
            'meilisearch_backup_interval',
            'meilisearch_backup_local_retention',
            'automatic_upgrades_enabled',
            'firewall_rules_external_providers_enabled',
            'site_id',
            'customer_id',
            'id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('clusters/%d', $cluster->getId()))
            ->setBody(
                $this->filterFields($cluster->toArray(), [
                    'name',
                    'groups',
                    'unix_users_home_directory',
                    'php_versions',
                    'mariadb_version',
                    'mariadb_cluster_name',
                    'php_settings',
                    'http_retry_properties',
                    'custom_php_modules_names',
                    'php_ioncube_enabled',
                    'kernelcare_license_key',
                    'redis_password',
                    'redis_memory_limit',
                    'nodejs_versions',
                    'nodejs_version',
                    'customer_id',
                    'wordpress_toolkit_enabled',
                    'database_toolkit_enabled',
                    'mariadb_backup_interval',
                    'mariadb_backup_local_retention',
                    'postgresql_version',
                    'postgresql_backup_interval',
                    'postgresql_backup_local_retention',
                    'malware_toolkit_enabled',
                    'malware_toolkit_scans_enabled',
                    'mariadb_toolkit_enabled',
                    'mariadb_toolkit_scans_enabled',
                    'bubblewrap_toolkit_enabled',
                    'sync_toolkit_enabled',
                    'automatic_borg_repositories_prune_enabled',
                    'php_sessions_spread_enabled',
                    'description',
                    'new_relic_apm_license_key',
                    'new_relic_infrastructure_license_key',
                    'new_relic_mariadb_password',
                    'meilisearch_master_key',
                    'meilisearch_environment',
                    'meilisearch_backup_interval',
                    'meilisearch_backup_local_retention',
                    'automatic_upgrades_enabled',
                    'firewall_rules_external_providers_enabled',
                    'site_id',
                    'customer_id',
                    'id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cluster' => (new Cluster())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('clusters/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function children(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('clusters/%d/children', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function unixUsersHomeDirectoryUsages(
        int $id,
        DateTimeInterface $from,
        string $timeUnit = TimeUnit::HOURLY
    ): Response {
        $url = sprintf(
            'clusters/unix-users-home-directories/usages/%d?%s',
            $id,
            http_build_query([
                'timestamp' => $from->format('c'),
                'time_unit' => $timeUnit,
            ])
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'unixUsersHomeDirectoryUsage' => (new UnixUsersHomeDirectoryUsage())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function borgSshKey(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('clusters/%d/borg-ssh-key', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'publicKey' => $response->getData('public_key'),
        ]);
    }

    public function commonProperties(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl('clusters/common-properties');

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'commonProperties' => (new ClusterCommonProperties())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function ipAddresses(int $clusterId): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('clusters/%d/ip-addresses', $clusterId));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $ipAddresses = [];
        foreach ($response->getData() as $name => $data) {
            $ipAddresses[$name] = (new HostIpAddress())->fromArray($data);
        }

        return $response->setData([
            'ipAddresses' => $ipAddresses,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function createIpAddress(int $clusterId, IpAddressCreate $ipAddress): Response
    {
        $this->validateRequired($ipAddress, 'create', [
            'service_account_name',
            'dns_name',
            'address_family',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('clusters/%d/ip-addresses', $clusterId))
            ->setBody(
                $this->filterFields($ipAddress->toArray(), [
                    'service_account_name',
                    'dns_name',
                    'address_family',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'taskCollection' => (new TaskCollection())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function deleteIpAddress(int $customerId, int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('clusters/%d/ip-addresses/%d', $customerId, $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function products(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl('clusters/ip-addresses/products');

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'ipAddressProducts' => array_map(
                fn (array $data) => (new IpAddressProduct())->fromArray($data),
                $response->getData()
            ),
        ]);
    }
}
