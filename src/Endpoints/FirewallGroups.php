<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\FirewallGroup;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class FirewallGroups extends Endpoint
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
            ->setUrl(sprintf('firewall-groups?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'firewallGroups' => array_map(
                fn (array $data) => (new FirewallGroup())->fromArray($data),
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
            ->setUrl(sprintf('firewall-groups/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'firewallGroup' => (new FirewallGroup())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(FirewallGroup $firewallGroup): Response
    {
        $this->validateRequired($firewallGroup, 'create', [
            'name',
            'ip_networks',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('firewall-groups')
            ->setBody(
                $this->filterFields($firewallGroup->toArray(), [
                    'name',
                    'ip_networks',
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
            'firewallGroup' => (new FirewallGroup())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(FirewallGroup $firewallGroup): Response
    {
        $this->validateRequired($firewallGroup, 'update', [
            'name',
            'ip_networks',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('firewall-groups/%d', $firewallGroup->getId()))
            ->setBody(
                $this->filterFields($firewallGroup->toArray(), [
                    'name',
                    'ip_networks',
                    'id',
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
            'firewallGroup' => (new FirewallGroup())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('firewall-groups/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
