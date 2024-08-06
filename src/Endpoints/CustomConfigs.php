<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\CustomConfig;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class CustomConfigs extends Endpoint
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
            ->setUrl(sprintf('custom-configs?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfigs' => array_map(
                fn (array $data) => (new CustomConfig())->fromArray($data),
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
            ->setUrl(sprintf('custom-configs/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfigs' => (new CustomConfig())->fromArray($response->getData())
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(CustomConfig $customConfig): Response
    {
        $this->validateRequired($customConfig, 'create', [
            'name',
            'server_software_name',
            'contents',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('custom-configs')
            ->setBody(
                $this->filterFields($customConfig->toArray(), [
                    'name',
                    'server_software_name',
                    'contents',
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
            'customConfig' => (new CustomConfig())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(CustomConfig $customConfig): Response
    {
        $this->validateRequired($customConfig, 'update', [
            'name',
            'server_software_name',
            'contents',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('custom-configs/%d', $customConfig->getId()))
            ->setBody(
                $this->filterFields($customConfig->toArray(), [
                    'name',
                    'server_software_name',
                    'contents',
                    'cluster_id',
                    'id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customConfig' => (new CustomConfig())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('custom-configs/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
