<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\DomainRouter;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class DomainRouters extends Endpoint
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
            ->setUrl(sprintf('domain-routers?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'domainRouters' => array_map(
                fn(array $data) => (new DomainRouter())->fromArray($data),
                $response->getData()
            ),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(DomainRouter $domainRouter): Response
    {
        $this->validateRequired($domainRouter, 'update', [
            'domain',
            'virtual_host_id',
            'url_redirect_id',
            'node_id',
            'force_ssl',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('domain-routers/%d', $domainRouter->getId()))
            ->setBody(
                $this->filterFields($domainRouter->toArray(), [
                    'domain',
                    'virtual_host_id',
                    'url_redirect_id',
                    'node_id',
                    'certificate_id',
                    'force_ssl',
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

        $domainRouter = (new DomainRouter())->fromArray($response->getData());

        return $response->setData([
            'domainRouter' => $domainRouter,
        ]);
    }
}
