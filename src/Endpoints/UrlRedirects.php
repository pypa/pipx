<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\UrlRedirect;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class UrlRedirects extends Endpoint
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
            ->setUrl(sprintf('url-redirects?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'urlRedirects' => array_map(
                function (array $data) {
                    return (new UrlRedirect())->fromArray($data);
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
            ->setUrl(sprintf('url-redirects/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'urlRedirect' => (new UrlRedirect())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param UrlRedirect $urlRedirect
     * @return Response
     * @throws RequestException
     */
    public function create(UrlRedirect $urlRedirect): Response
    {
        $this->validateRequired($urlRedirect, 'create', [
            'domain',
            'server_aliases',
            'destination_url',
            'status_code',
            'keep_query_parameters',
            'keep_path',
            'force_ssl',
            'balancer_backend_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('url-redirects')
            ->setBody($this->filterFields($urlRedirect->toArray(), [
                'domain',
                'server_aliases',
                'destination_url',
                'status_code',
                'keep_query_parameters',
                'keep_path',
                'force_ssl',
                'balancer_backend_name',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $urlRedirect = (new UrlRedirect())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($urlRedirect->getClusterId());

        return $response->setData([
            'urlRedirect' => $urlRedirect,
        ]);
    }

    /**
     * @param UrlRedirect $urlRedirect
     * @return Response
     * @throws RequestException
     */
    public function update(UrlRedirect $urlRedirect): Response
    {
        $this->validateRequired($urlRedirect, 'update', [
            'domain',
            'server_aliases',
            'destination_url',
            'status_code',
            'keep_query_parameters',
            'keep_path',
            'force_ssl',
            'balancer_backend_name',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('url-redirects/%d', $urlRedirect->getId()))
            ->setBody($this->filterFields($urlRedirect->toArray(), [
                'domain',
                'server_aliases',
                'destination_url',
                'status_code',
                'keep_query_parameters',
                'keep_path',
                'force_ssl',
                'balancer_backend_name',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $urlRedirect = (new UrlRedirect())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($urlRedirect->getClusterId());

        return $response->setData([
            'urlRedirect' => $urlRedirect,
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
                ->getData('urlRedirect')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('url-redirects/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
