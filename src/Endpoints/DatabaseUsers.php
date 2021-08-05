<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\DatabaseUser;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class DatabaseUsers extends Endpoint
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
            ->setUrl(sprintf('database-users?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUsers' => array_map(
                function (array $data) {
                    return (new DatabaseUser())->fromArray($data);
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
            ->setUrl(sprintf('database-users/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUser' => (new DatabaseUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param DatabaseUser $databaseUser
     * @return Response
     * @throws RequestException
     */
    public function create(DatabaseUser $databaseUser): Response
    {
        $this->validateRequired($databaseUser, 'create', [
            'name',
            'password',
            'server_software_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('database-users')
            ->setBody($this->filterFields($databaseUser->toArray(), [
                'name',
                'host',
                'password',
                'server_software_name',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        $databaseUser = (new DatabaseUser())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($databaseUser->getClusterId());

        return $response->setData([
            'databaseUser' => $databaseUser,
        ]);
    }

    /**
     * @param DatabaseUser $databaseUser
     * @return Response
     * @throws RequestException
     */
    public function update(DatabaseUser $databaseUser): Response
    {
        $this->validateRequired($databaseUser, 'update', [
            'id',
            'name',
            'password',
            'server_software_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('database-users/%d', $databaseUser->getId()))
            ->setBody($this->filterFields($databaseUser->toArray(), [
                'name',
                'host',
                'password',
                'server_software_name',
                'cluster_id',
                'id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        $databaseUser = (new DatabaseUser())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($databaseUser->getClusterId());

        return $response->setData([
            'databaseUser' => $databaseUser,
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
                ->getData('databaseUser')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('database-users/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
