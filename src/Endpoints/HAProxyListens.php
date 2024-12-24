<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\HAProxyListen;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class HAProxyListens extends Endpoint
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
            ->setUrl(sprintf('haproxy-listens?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'haProxyListens' => array_map(
                fn (array $data) => (new HAProxyListen())->fromArray($data),
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
            ->setUrl(sprintf('haproxy-listens/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'haProxyListen' => (new HAProxyListen())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(HAProxyListen $haProxyListen): Response
    {
        $this->validateRequired($haProxyListen, 'create', [
            'name',
            'nodes_group',
            'nodes_ids',
            'port',
            'socket_path',
            'destination_cluster_id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('haproxy-listens')
            ->setBody(
                $this->filterFields($haProxyListen->toArray(), [
                    'name',
                    'nodes_group',
                    'nodes_ids',
                    'port',
                    'socket_path',
                    'destination_cluster_id',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'haProxyListens' => (new HAProxyListen())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('haproxy-listens/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
