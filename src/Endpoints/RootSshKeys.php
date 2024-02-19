<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\RootSshKey;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class RootSshKeys extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if ($filter === null) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('root-ssh-keys?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'rootSshKeys' => array_map(
                fn (array $data) => (new RootSshKey())->fromArray($data),
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
            ->setUrl(sprintf('root-ssh-keys/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'rootSshKey' => (new RootSshKey())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function createPublic(RootSshKey $rootSshKey): Response
    {
        $this->validateRequired($rootSshKey, 'create', [
            'name',
            'public_key',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('root-ssh-keys/public')
            ->setBody(
                $this->filterFields($rootSshKey->toArray(), [
                    'name',
                    'public_key',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $rootSshKey = (new RootSshKey())->fromArray($response->getData());

        return $response->setData([
            'rootSshKey' => $rootSshKey,
        ]);
    }

    public function createPrivate(RootSshKey $rootSshKey): Response
    {
        $this->validateRequired($rootSshKey, 'create', [
            'name',
            'private_key',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('root-ssh-keys/public')
            ->setBody(
                $this->filterFields($rootSshKey->toArray(), [
                    'name',
                    'private_key',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $rootSshKey = (new RootSshKey())->fromArray($response->getData());

        return $response->setData([
            'rootSshKey' => $rootSshKey,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('root-ssh-keys/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
