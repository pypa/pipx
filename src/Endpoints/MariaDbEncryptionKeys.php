<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\MariaDbEncryptionKey;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class MariaDbEncryptionKeys extends Endpoint
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
            ->setUrl(sprintf('mariadb-encryption-keys?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mariaDbEncryptionKeys' => array_map(
                fn (array $data) => (new MariaDbEncryptionKey())->fromArray($data),
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
            ->setUrl(sprintf('mariadb-encryption-keys/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mariaDbEncryptionKey' => (new MariaDbEncryptionKey())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(int $clusterId): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mariadb-encryption-keys')
            ->setBody([
                'cluster_id' => $clusterId
            ]);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mariaDbEncryptionKey' => (new MariaDbEncryptionKey())->fromArray($response->getData()),
        ]);
    }
}
