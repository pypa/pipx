<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\FpmPool;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Support\Str;

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
                'log_slow_requests_threshold',
                'is_namespaced',
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
                'log_slow_requests_threshold',
                'is_namespaced',
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
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function restart(int $id, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('fpm-pools/%d/restart', $id),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $taskCollection = (new TaskCollection())->fromArray($response->getData());

        return $response->setData([
            'taskCollection' => $taskCollection,
        ]);
    }

    /**
     * @param int $id
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function reload(int $id, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('fpm-pools/%d/reload', $id),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $taskCollection = (new TaskCollection())->fromArray($response->getData());

        return $response->setData([
            'taskCollection' => $taskCollection,
        ]);
    }
}
