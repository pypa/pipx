<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\UnixUser;
use Vdhicts\Cyberfusion\ClusterApi\Models\UnixUserUsage;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

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
            ->setUrl(sprintf('unix-users?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
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
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'unixUser' => (new UnixUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function usages(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('unix-users/usages/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
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
        $requiredAttributes = [
            'username',
            'password',
            'defaultPhpVersion',
            'clusterId',
        ];
        $this->validateRequired($unixUser, 'create', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('unix-users')
            ->setBody($this->filterFields($unixUser->toArray(), [
                'username',
                'password',
                'default_php_version',
                'virtual_hosts_directory',
                'mail_domains_directory',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'unixUser' => (new UnixUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param UnixUser $unixUser
     * @return Response
     * @throws RequestException
     */
    public function update(UnixUser $unixUser): Response
    {
        $requiredAttributes = [
            'username',
            'password',
            'defaultPhpVersion',
            'id',
            'clusterId',
            'unixId',
        ];
        $this->validateRequired($unixUser, 'update', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('unix-users/%d', $unixUser->id))
            ->setBody($this->filterFields($unixUser->toArray(), [
                'username',
                'password',
                'default_php_version',
                'virtual_hosts_directory',
                'mail_domains_directory',
                'id',
                'cluster_id',
                'unix_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'unixUser' => (new UnixUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @return Response
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
}
