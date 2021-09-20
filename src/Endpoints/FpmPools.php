<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\FpmPool;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class FpmPools extends Endpoint
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
            ->setUrl(sprintf('fpm-pools?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'fpmPools' => array_map(
                function (array $data) {
                    return (new FpmPool())->fromArray($data);
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
            ->setUrl(sprintf('fpm-pools/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'fpmPool' => (new FpmPool())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param FpmPool $fpmPool
     * @return Response
     * @throws RequestException
     */
    public function create(FpmPool $fpmPool): Response
    {
        $this->validateRequired($fpmPool, 'create', [
            'name',
            'unix_user_id',
            'version',
            'max_children',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('fpm-pools')
            ->setBody($this->filterFields($fpmPool->toArray(), [
                'name',
                'unix_user_id',
                'version',
                'max_children',
                'max_requests',
                'process_idle_timeout',
                'cpu_limit',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $fpmPool = (new FpmPool())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($fpmPool->getClusterId());

        return $response->setData([
            'fpmPool' => $fpmPool,
        ]);
    }

    /**
     * @param FpmPool $fpmPool
     * @return Response
     * @throws RequestException
     */
    public function update(FpmPool $fpmPool): Response
    {
        $this->validateRequired($fpmPool, 'update', [
            'name',
            'unix_user_id',
            'version',
            'max_children',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('fpm-pools/%d', $fpmPool->getId()))
            ->setBody($this->filterFields($fpmPool->toArray(), [
                'name',
                'unix_user_id',
                'version',
                'max_children',
                'max_requests',
                'process_idle_timeout',
                'cpu_limit',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $fpmPool = (new FpmPool())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($fpmPool->getClusterId());

        return $response->setData([
            'fpmPool' => $fpmPool,
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
                ->getData('fpmPool')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('fpm-pools/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function restart(int $id)
    {
        $result = $this->get($id);
        if ($result->isSuccess()) {
            $clusterId = $result
                ->getData('fpmPool')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('fpm-pools/%d/restart', $id));

        return $this
            ->client
            ->request($request);
    }
}
