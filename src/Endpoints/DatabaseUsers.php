<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\DatabaseUser;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class DatabaseUsers extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if (!$filter instanceof ListFilter) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('database-users?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUsers' => array_map(
                fn (array $data) => (new DatabaseUser())->fromArray($data),
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
            ->setUrl(sprintf('database-users/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUser' => (new DatabaseUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(DatabaseUser $databaseUser): Response
    {
        $this->validateRequired($databaseUser, 'create', [
            'name',
            'password',
            'phpmyadmin_firewall_groups_ids',
            'server_software_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('database-users')
            ->setBody(
                $this->filterFields($databaseUser->toArray(), [
                    'name',
                    'host',
                    'password',
                    'phpmyadmin_firewall_groups_ids',
                    'server_software_name',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $databaseUser = (new DatabaseUser())->fromArray($response->getData());

        return $response->setData([
            'databaseUser' => $databaseUser,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(DatabaseUser $databaseUser): Response
    {
        $this->validateRequired($databaseUser, 'update', [
            'id',
            'name',
            'password',
            'phpmyadmin_firewall_groups_ids',
            'server_software_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('database-users/%d', $databaseUser->getId()))
            ->setBody(
                $this->filterFields($databaseUser->toArray(), [
                    'name',
                    'host',
                    'password',
                    'phpmyadmin_firewall_groups_ids',
                    'server_software_name',
                    'cluster_id',
                    'id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $databaseUser = (new DatabaseUser())->fromArray($response->getData());

        return $response->setData([
            'databaseUser' => $databaseUser,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('database-users/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
