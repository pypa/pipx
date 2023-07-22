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
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
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
                fn (array $data) => (new UnixUser())->fromArray($data),
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
                    fn (array $data) => (new UnixUserUsage())->fromArray($data),
                    $response->getData()
                )
                : null,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(UnixUser $unixUser): Response
    {
        $this->validateRequired($unixUser, 'create', [
            'username',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('unix-users')
            ->setBody(
                $this->filterFields($unixUser->toArray(), [
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
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $unixUser = (new UnixUser())->fromArray($response->getData());

        return $response->setData([
            'unixUser' => $unixUser,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(UnixUser $unixUser): Response
    {
        $this->validateRequired($unixUser, 'update', [
            'username',
            'id',
            'cluster_id',
            'unix_id',
            'home_directory',
            'ssh_directory',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('unix-users/%d', $unixUser->getId()))
            ->setBody(
                $this->filterFields($unixUser->toArray(), [
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
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $unixUser = (new UnixUser())->fromArray($response->getData());

        return $response->setData([
            'unixUser' => $unixUser,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('unix-users/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
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
