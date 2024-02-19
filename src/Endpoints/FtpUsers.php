<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\FtpUser;
use Cyberfusion\ClusterApi\Models\TemporaryFtpUser;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class FtpUsers extends Endpoint
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
            ->setUrl(sprintf('ftp-users?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'ftpUsers' => array_map(
                fn (array $data) => (new FtpUser())->fromArray($data),
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
            ->setUrl(sprintf('ftp-users/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'ftpUser' => (new FtpUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(FtpUser $ftpUser): Response
    {
        $this->validateRequired($ftpUser, 'create', [
            'name',
            'password',
            'directory_path',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('ftp-users')
            ->setBody(
                $this->filterFields($ftpUser->toArray(), [
                    'name',
                    'password',
                    'directory_path',
                    'unix_user_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'ftpUser' => (new FtpUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(FtpUser $ftpUser): Response
    {
        $this->validateRequired($ftpUser, 'update', [
            'username',
            'password',
            'directory_path',
            'unix_user_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('ftp-users/%d', $ftpUser->getId()))
            ->setBody(
                $this->filterFields($ftpUser->toArray(), [
                    'username',
                    'password',
                    'directory_path',
                    'unix_user_id',
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
            'ftpUser' => (new FtpUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('ftp-users/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function temporary(int $unixUserId, int $nodeId): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('ftp-users/temporary')
            ->setBody([
                'unix_user_id' => $unixUserId,
                'node_id' => $nodeId,
            ]);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'temporaryFtpUser' => (new TemporaryFtpUser())->fromArray($response->getData()),
        ]);
    }
}
