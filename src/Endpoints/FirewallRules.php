<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\FirewallRule;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class FirewallRules extends Endpoint
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
            ->setUrl(sprintf('firewall-rules?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailAccounts' => array_map(
                fn (array $data) => (new FirewallRule())->fromArray($data),
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
            ->setUrl(sprintf('firewall-rules/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'firewallRule' => (new FirewallRule())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(FirewallRule $firewallRule): Response
    {
        $this->validateRequired($firewallRule, 'create', [
            'node_id',
            'firewall_group_id',
            'external_provider_name',
            'service_name',
            'haproxy_listen_id',
            'port',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('firewall-rules')
            ->setBody(
                $this->filterFields($firewallRule->toArray(), [
                    'node_id',
                    'firewall_group_id',
                    'external_provider_name',
                    'service_name',
                    'haproxy_listen_id',
                    'port',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'firewallRule' => (new FirewallRule())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(FirewallRule $firewallRule): Response
    {
        $this->validateRequired($firewallRule, 'update', [
            'node_id',
            'firewall_group_id',
            'external_provider_name',
            'service_name',
            'haproxy_listen_id',
            'port',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('firewall-rules/%d', $firewallRule->getId()))
            ->setBody(
                $this->filterFields($firewallRule->toArray(), [
                    'node_id',
                    'firewall_group_id',
                    'external_provider_name',
                    'service_name',
                    'haproxy_listen_id',
                    'port',
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
            'firewallRule' => (new FirewallRule())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('firewall-rules/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
