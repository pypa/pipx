<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\ListFilterException;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\HAProxyListenToNode;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class HAProxyListensToNodes extends Endpoint
{
    /**
     * @throws RequestException
     * @throws ListFilterException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if ($filter === null) {
            $filter = HAProxyListenToNode::listFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('haproxy-listens-to-nodes?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'HAProxyListensToNodes' => array_map(
                fn (array $data) => (new HAProxyListenToNode())->fromArray($data),
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
            ->setUrl(sprintf('haproxy-listens-to-nodes/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'haProxyListenToNode' => (new HAProxyListenToNode())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(HAProxyListenToNode $haProxyListenToNode): Response
    {
        $this->validateRequired($haProxyListenToNode, 'create', [
            'haproxy_listen_id',
            'node_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('haproxy-listens-to-nodes')
            ->setBody(
                $this->filterFields($haProxyListenToNode->toArray(), [
                    'haproxy_listen_id',
                    'node_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'haProxyListenToNode' => (new HAProxyListenToNode())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('haproxy-listens-to-nodes/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
