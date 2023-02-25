<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\UrlRedirect;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class UrlRedirects extends Endpoint
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
            ->setUrl(sprintf('url-redirects?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'urlRedirects' => array_map(
                fn(array $data) => (new UrlRedirect())->fromArray($data),
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
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('url-redirects')
            ->setBody(
                $this->filterFields($urlRedirect->toArray(), [
                    'domain',
                    'server_aliases',
                    'destination_url',
                    'status_code',
                    'keep_query_parameters',
                    'keep_path',
                    'description',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $urlRedirect = (new UrlRedirect())->fromArray($response->getData());

        return $response->setData([
            'urlRedirect' => $urlRedirect,
        ]);
    }

    /**
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
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('url-redirects/%d', $urlRedirect->getId()))
            ->setBody(
                $this->filterFields($urlRedirect->toArray(), [
                    'domain',
                    'server_aliases',
                    'destination_url',
                    'status_code',
                    'keep_query_parameters',
                    'keep_path',
                    'description',
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

        $urlRedirect = (new UrlRedirect())->fromArray($response->getData());

        return $response->setData([
            'urlRedirect' => $urlRedirect,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('url-redirects/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
