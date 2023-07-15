<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\CustomConfigSnippet;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class CustomConfigSnippets extends Endpoint
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
            ->setUrl(sprintf('custom-config-snippets?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfigSnippets' => array_map(
                fn (array $data) => (new CustomConfigSnippet())->fromArray($data),
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
            ->setUrl(sprintf('custom-config-snippets/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfigSnippet' => (new CustomConfigSnippet())->fromArray($response->getData())
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(CustomConfigSnippet $customConfigSnippet): Response
    {
        $this->validateRequired($customConfigSnippet, 'create', [
            'name',
            'server_software_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('custom-config-snippets')
            ->setBody(
                $this->filterFields($customConfigSnippet->toArray(), [
                    'name',
                    'server_software_name',
                    'cluster_id',
                    'contents',
                    'template_name',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfigSnippet' => (new CustomConfigSnippet())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(CustomConfigSnippet $customConfigSnippet): Response
    {
        $this->validateRequired($customConfigSnippet, 'update', [
            'name',
            'server_software_name',
            'cluster_id',
            'id',
            'contents',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('custom-config-snippets/%d', $customConfigSnippet->getId()))
            ->setBody(
                $this->filterFields($customConfigSnippet->toArray(), [
                    'name',
                    'server_software_name',
                    'cluster_id',
                    'id',
                    'contents',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfigSnippet' => (new CustomConfigSnippet())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('custom-config-snippets/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
