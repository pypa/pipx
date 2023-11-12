<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Node;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class Nodes extends Endpoint
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
            ->setUrl(sprintf('nodes?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'nodes' => array_map(
                fn (array $data) => (new Node())->fromArray($data),
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
            ->setUrl(sprintf('nodes/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'node' => (new Node())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(Node $node): Response
    {
        $this->validateRequired($node, 'create', [
            'groups',
            'comment',
            'load_balancer_health_checks_groups_pairs',
            'groups_properties',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('nodes')
            ->setBody(
                $this->filterFields($node->toArray(), [
                    'groups',
                    'comment',
                    'load_balancer_health_checks_groups_pairs',
                    'groups_properties',
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
            'taskCollection' => (new TaskCollection())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(Node $node): Response
    {
        $this->validateRequired($node, 'update', [
            'groups',
            'comment',
            'load_balancer_health_checks_groups_pairs',
            'groups_properties',
            'cluster_id',
            'id',
            'hostname',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('nodes/%d', $node->getId()))
            ->setBody(
                $this->filterFields($node->toArray(), [
                    'groups',
                    'comment',
                    'load_balancer_health_checks_groups_pairs',
                    'groups_properties',
                    'cluster_id',
                    'id',
                    'hostname',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'node' => (new Node())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('nodes/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
