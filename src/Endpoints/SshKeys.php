<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\SshKey;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

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
            ->setUrl(sprintf('ssh-keys?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
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
        if (! $response->isSuccess()) {
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
    public function create(SshKey $sshKey): Response
    {
        $requiredAttributes = [
            'name',
            'publicKey',
            'unixUserId',
        ];
        $this->validateRequired($sshKey, 'create', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('ssh-keys')
            ->setBody($this->filterFields($sshKey->toArray(), [
                'name',
                'public_key',
                'unix_user_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
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
    public function update(SshKey $sshKey): Response
    {
        $requiredAttributes = [
            'name',
            'publicKey',
            'unixUserId',
            'id',
            'clusterId'
        ];
        $this->validateRequired($sshKey, 'update', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('ssh-keys/%d', $sshKey->id))
            ->setBody($this->filterFields($sshKey->toArray(), [
                'name',
                'public_key',
                'unix_user_id',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'sshKey' => (new SshKey())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('ssh-keys/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
