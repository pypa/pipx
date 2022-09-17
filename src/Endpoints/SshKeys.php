<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\SshKey;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class SshKeys extends Endpoint
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
            ->setUrl(sprintf('ssh-keys?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'sshKeys' => array_map(
                function (array $data) {
                    return (new SshKey())->fromArray($data);
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
            ->setUrl(sprintf('ssh-keys/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'sshKey' => (new SshKey())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param SshKey $sshKey
     * @return Response
     * @throws RequestException
     */
    public function createPublic(SshKey $sshKey): Response
    {
        $this->validateRequired($sshKey, 'create', [
            'name',
            'public_key',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('ssh-keys/public')
            ->setBody($this->filterFields($sshKey->toArray(), [
                'name',
                'public_key',
                'unix_user_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $sshKey = (new SshKey())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($sshKey->getClusterId());

        return $response->setData([
            'sshKey' => $sshKey,
        ]);
    }

    public function createPrivate(SshKey $sshKey): Response
    {
        $this->validateRequired($sshKey, 'create', [
            'name',
            'private_key',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('ssh-keys/public')
            ->setBody($this->filterFields($sshKey->toArray(), [
                'name',
                'private_key',
                'unix_user_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $sshKey = (new SshKey())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($sshKey->getClusterId());

        return $response->setData([
            'sshKey' => $sshKey,
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
                ->getData('sshKey')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('ssh-keys/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
