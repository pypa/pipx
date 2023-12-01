<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Enums\TimeUnit;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Cluster;
use Cyberfusion\ClusterApi\Models\ClusterCommonProperties;
use Cyberfusion\ClusterApi\Models\HostIpAddress;
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
        if (is_null($filter)) {
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
            'nodejs_version',
            'postgresql_version',
            'mariadb_cluster_name',
            'custom_php_modules_names',
            'php_settings',
            'php_ioncube_enabled',
            'kernelcare_license_key',
            'new_relic_apm_license_key',
            'new_relic_infrastructure_license_key',
            'new_relic_mariadb_password',
            'meilisearch_master_key',
            'meilisearch_environment',
            'meilisearch_backup_interval',
            'redis_password',
            'redis_memory_limit',
            'php_sessions_spread_enabled',
            'nodejs_versions',
            'description',
            'wordpress_toolkit_enabled',
            'automatic_borg_repositories_prune_enabled',
            'malware_toolkit_enabled',
            'sync_toolkit_enabled',
            'bubblewrap_toolkit_enabled',
            'malware_toolkit_scans_enabled',
            'database_toolkit_enabled',
            'mariadb_backup_interval',
            'postgresql_backup_interval',
            'customer_id',
            'http_retry_properties',
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
                    'nodejs_version',
                    'postgresql_version',
                    'mariadb_cluster_name',
                    'custom_php_modules_names',
                    'php_settings',
                    'php_ioncube_enabled',
                    'kernelcare_license_key',
                    'new_relic_apm_license_key',
                    'new_relic_infrastructure_license_key',
                    'new_relic_mariadb_password',
                    'meilisearch_master_key',
                    'meilisearch_environment',
                    'meilisearch_backup_interval',
                    'redis_password',
                    'redis_memory_limit',
                    'php_sessions_spread_enabled',
                    'nodejs_versions',
                    'description',
                    'wordpress_toolkit_enabled',
                    'automatic_borg_repositories_prune_enabled',
                    'malware_toolkit_enabled',
                    'sync_toolkit_enabled',
                    'bubblewrap_toolkit_enabled',
                    'malware_toolkit_scans_enabled',
                    'database_toolkit_enabled',
                    'mariadb_backup_interval',
                    'postgresql_backup_interval',
                    'customer_id',
                    'http_retry_properties',
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
            'nodejs_version',
            'postgresql_version',
            'mariadb_cluster_name',
            'custom_php_modules_names',
            'php_settings',
            'php_ioncube_enabled',
            'kernelcare_license_key',
            'new_relic_apm_license_key',
            'new_relic_infrastructure_license_key',
            'new_relic_mariadb_password',
            'meilisearch_master_key',
            'meilisearch_environment',
            'meilisearch_backup_interval',
            'redis_password',
            'redis_memory_limit',
            'php_sessions_spread_enabled',
            'nodejs_versions',
            'description',
            'wordpress_toolkit_enabled',
            'automatic_borg_repositories_prune_enabled',
            'malware_toolkit_enabled',
            'sync_toolkit_enabled',
            'bubblewrap_toolkit_enabled',
            'malware_toolkit_scans_enabled',
            'database_toolkit_enabled',
            'mariadb_backup_interval',
            'postgresql_backup_interval',
            'customer_id',
            'id',
            'http_retry_properties',
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
                    'nodejs_version',
                    'postgresql_version',
                    'mariadb_cluster_name',
                    'custom_php_modules_names',
                    'php_settings',
                    'php_ioncube_enabled',
                    'kernelcare_license_key',
                    'new_relic_apm_license_key',
                    'new_relic_infrastructure_license_key',
                    'new_relic_mariadb_password',
                    'meilisearch_master_key',
                    'meilisearch_environment',
                    'meilisearch_backup_interval',
                    'redis_password',
                    'redis_memory_limit',
                    'php_sessions_spread_enabled',
                    'nodejs_versions',
                    'description',
                    'wordpress_toolkit_enabled',
                    'automatic_borg_repositories_prune_enabled',
                    'malware_toolkit_enabled',
                    'sync_toolkit_enabled',
                    'bubblewrap_toolkit_enabled',
                    'malware_toolkit_scans_enabled',
                    'database_toolkit_enabled',
                    'mariadb_backup_interval',
                    'postgresql_backup_interval',
                    'customer_id',
                    'id',
                    'http_retry_properties',
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
}
