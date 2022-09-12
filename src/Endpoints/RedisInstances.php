<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\RedisInstance;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class RedisInstances extends Endpoint
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
            ->setUrl(sprintf('redis-instances?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'redisInstances' => array_map(
                function (array $data) {
                    return (new RedisInstance())->fromArray($data);
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
            ->setUrl(sprintf('redis-instances/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'redisInstance' => (new RedisInstance())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param RedisInstance $redisInstance
     * @return Response
     * @throws RequestException
     */
    public function create(RedisInstance $redisInstance): Response
    {
        $this->validateRequired($redisInstance, 'create', [
            'name',
            'password',
            'max_databases',
            'primary_node_id',
            'memory_limit',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('redis-instances')
            ->setBody($this->filterFields($redisInstance->toArray(), [
                'name',
                'password',
                'max_databases',
                'primary_node_id',
                'memory_limit',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $redisInstance = (new RedisInstance())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($redisInstance->getClusterId());

        return $response->setData([
            'redisInstance' => $redisInstance,
        ]);
    }

    /**
     * @param RedisInstance $redisInstance
     * @return Response
     * @throws RequestException
     */
    public function update(RedisInstance $redisInstance): Response
    {
        $this->validateRequired($redisInstance, 'update', [
            'name',
            'password',
            'max_databases',
            'primary_node_id',
            'memory_limit',
            'port',
            'unit_name',
            'cluster_id',
            'id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('redis-instances/%d', $redisInstance->getId()))
            ->setBody($this->filterFields($redisInstance->toArray(), [
                'name',
                'password',
                'max_databases',
                'primary_node_id',
                'memory_limit',
                'port',
                'unit_name',
                'cluster_id',
                'id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $redisInstance = (new RedisInstance())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($redisInstance->getClusterId());

        return $response->setData([
            'redisInstance' => $redisInstance,
        ]);
    }
}
