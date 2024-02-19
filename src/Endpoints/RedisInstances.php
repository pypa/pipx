<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\RedisInstance;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class RedisInstances extends Endpoint
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
            ->setUrl(sprintf('redis-instances?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'redisInstances' => array_map(
                fn (array $data) => (new RedisInstance())->fromArray($data),
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
     * @throws RequestException
     */
    public function create(RedisInstance $redisInstance): Response
    {
        $this->validateRequired($redisInstance, 'create', [
            'name',
            'password',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('redis-instances')
            ->setBody(
                $this->filterFields($redisInstance->toArray(), [
                    'name',
                    'password',
                    'memory_limit',
                    'eviction_policy',
                    'max_databases',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $redisInstance = (new RedisInstance())->fromArray($response->getData());

        return $response->setData([
            'redisInstance' => $redisInstance,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(RedisInstance $redisInstance): Response
    {
        $this->validateRequired($redisInstance, 'update', [
            'name',
            'password',
            'cluster_id',
            'id',
            'port',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('redis-instances/%d', $redisInstance->getId()))
            ->setBody(
                $this->filterFields($redisInstance->toArray(), [
                    'name',
                    'password',
                    'max_databases',
                    'memory_limit',
                    'eviction_policy',
                    'cluster_id',
                    'id',
                    'port',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $redisInstance = (new RedisInstance())->fromArray($response->getData());

        return $response->setData([
            'redisInstance' => $redisInstance,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('redis-instances/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
