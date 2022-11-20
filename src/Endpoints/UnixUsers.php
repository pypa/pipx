<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Enums\TimeUnit;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\UnixUser;
use Cyberfusion\ClusterApi\Models\UnixUserComparison;
use Cyberfusion\ClusterApi\Models\UnixUserUsage;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use DateTimeInterface;

class UnixUsers extends Endpoint
{
    /**
     * @param ListFilter|null $filter
     * @return Response
     * @throws RequestException
     */
    public function list(ListFilter $filter = null): Response
    {
        if (is_null($filter)) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('unix-users?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'unixUsers' => array_map(
                function (array $data) {
                    return (new UnixUser())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function get(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('unix-users/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'unixUser' => (new UnixUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @param DateTimeInterface $from
     * @param string $timeUnit
     * @return Response
     * @throws RequestException
     */
    public function usages(int $id, DateTimeInterface $from, string $timeUnit = TimeUnit::HOURLY): Response
    {
        $url = sprintf(
            'unix-users/usages/%d?%s',
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
            'unixUserUsage' => count($response->getData()) !== 0
                ? array_map(
                    function (array $data) {
                        return (new UnixUserUsage())->fromArray($data);
                    },
                    $response->getData()
                )
                : null,
        ]);
    }

    /**
     * @param UnixUser $unixUser
     * @return Response
     * @throws RequestException
     */
    public function create(UnixUser $unixUser): Response
    {
        $this->validateRequired($unixUser, 'create', [
            'username',
            'password',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('unix-users')
            ->setBody($this->filterFields($unixUser->toArray(), [
                'username',
                'password',
                'shell_path',
                'record_usage_files',
                'default_php_version',
                'default_nodejs_version',
                'virtual_hosts_directory',
                'mail_domains_directory',
                'borg_repositories_directory',
                'description',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $unixUser = (new UnixUser())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($unixUser->getClusterId());

        return $response->setData([
            'unixUser' => $unixUser,
        ]);
    }

    /**
     * @param UnixUser $unixUser
     * @return Response
     * @throws RequestException
     */
    public function update(UnixUser $unixUser): Response
    {
        $this->validateRequired($unixUser, 'update', [
            'username',
            'password',
            'id',
            'cluster_id',
            'unix_id',
            'home_directory',
            'ssh_directory',
            'rabbitmq_username',
            'rabbitmq_virtual_host_name',
            'rabbitmq_password',
            'rabbitmq_encryption_key',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('unix-users/%d', $unixUser->getId()))
            ->setBody($this->filterFields($unixUser->toArray(), [
                'username',
                'password',
                'shell_path',
                'record_usage_files',
                'default_php_version',
                'default_nodejs_version',
                'virtual_hosts_directory',
                'mail_domains_directory',
                'borg_repositories_directory',
                'description',
                'cluster_id',
                'id',
                'unix_id',
                'home_directory',
                'ssh_directory',
                'async_support_enabled',
                'rabbitmq_username',
                'rabbitmq_virtual_host_name',
                'rabbitmq_password',
                'rabbitmq_encryption_key',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $unixUser = (new UnixUser())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($unixUser->getClusterId());

        return $response->setData([
            'unixUser' => $unixUser,
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        // Log the affected cluster by retrieving the model first
        $result = $this->get($id);
        if ($result->isSuccess()) {
            $clusterId = $result
                ->getData('unixUser')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('unix-users/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function enableAsync(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('unix-users/%d/async-support', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $unixUser = (new UnixUser())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($unixUser->getClusterId());

        return $response->setData([
            'unixUser' => $unixUser,
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function disableAsync(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('unix-users/%d/async-support', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $unixUser = (new UnixUser())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($unixUser->getClusterId());

        return $response->setData([
            'unixUser' => $unixUser,
        ]);
    }

    /**
     * @param int $leftUnixUserId
     * @param int $rightUnixUserId
     * @return Response
     * @throws RequestException
     */
    public function compareTo(int $leftUnixUserId, int $rightUnixUserId): Response
    {
        $url = sprintf(
            'unix-users/%d/comparison?right_unix_user_id=%d',
            $leftUnixUserId,
            $rightUnixUserId
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
            'unixUserComparison' => (new UnixUserComparison())->fromArray($response->getData()),
        ]);
    }
}
