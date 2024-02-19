<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\HtpasswdUser;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class HtpasswdUsers extends Endpoint
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
            ->setUrl(sprintf('htpasswd-users?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'htpasswdUsers' => array_map(
                fn (array $data) => (new HtpasswdUser())->fromArray($data),
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
            ->setUrl(sprintf('htpasswd-users/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'htpasswdUser' => (new HtpasswdUser())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(HtpasswdUser $htpasswdUser): Response
    {
        $this->validateRequired($htpasswdUser, 'create', [
            'username',
            'password',
            'htpasswd_file_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('htpasswd-users')
            ->setBody(
                $this->filterFields($htpasswdUser->toArray(), [
                    'username',
                    'password',
                    'htpasswd_file_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $htpasswdUser = (new HtpasswdUser())->fromArray($response->getData());

        return $response->setData([
            'htpasswdUser' => $htpasswdUser,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(HtpasswdUser $htpasswdUser): Response
    {
        $this->validateRequired($htpasswdUser, 'update', [
            'username',
            'password',
            'htpasswd_file_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('htpasswd-users/%d', $htpasswdUser->getId()))
            ->setBody(
                $this->filterFields($htpasswdUser->toArray(), [
                    'username',
                    'password',
                    'htpasswd_file_id',
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

        $htpasswdUser = (new HtpasswdUser())->fromArray($response->getData());

        return $response->setData([
            'htpasswdUser' => $htpasswdUser,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('htpasswd-users/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
