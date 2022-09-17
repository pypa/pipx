<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\BasicAuthenticationRealm;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class BasicAuthenticationRealms extends Endpoint
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
            ->setUrl(sprintf('basic-authentication-realms?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'basicAuthenticationRealms' => array_map(
                function (array $data) {
                    return (new BasicAuthenticationRealm())->fromArray($data);
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
            ->setUrl(sprintf('basic-authentication-realms/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'basicAuthenticationRealm' => (new BasicAuthenticationRealm())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param BasicAuthenticationRealm $basicAuthenticationRealm
     * @return Response
     * @throws RequestException
     */
    public function create(BasicAuthenticationRealm $basicAuthenticationRealm): Response
    {
        $this->validateRequired($basicAuthenticationRealm, 'create', [
            'name',
            'directory_path',
            'htpasswd_file_id',
            'virtual_host_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('basic-authentication-realms')
            ->setBody($this->filterFields($basicAuthenticationRealm->toArray(), [
                'name',
                'directory_path',
                'htpasswd_file_id',
                'virtual_host_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $basicAuthenticationRealm = (new BasicAuthenticationRealm())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($basicAuthenticationRealm->getClusterId());

        return $response->setData([
            'basicAuthenticationRealm' => $basicAuthenticationRealm,
        ]);
    }

    /**
     * @param BasicAuthenticationRealm $basicAuthenticationRealm
     * @return Response
     * @throws RequestException
     */
    public function update(BasicAuthenticationRealm $basicAuthenticationRealm): Response
    {
        $this->validateRequired($basicAuthenticationRealm, 'update', [
            'name',
            'directory_path',
            'htpasswd_file_id',
            'virtual_host_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('basic-authentication-realms/%d', $basicAuthenticationRealm->getId()))
            ->setBody($this->filterFields($basicAuthenticationRealm->toArray(), [
                'name',
                'directory_path',
                'htpasswd_file_id',
                'virtual_host_id',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $basicAuthenticationRealm = (new BasicAuthenticationRealm())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($basicAuthenticationRealm->getClusterId());

        return $response->setData([
            'basicAuthenticationRealm' => $basicAuthenticationRealm,
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
                ->getData('basicAuthenticationRealm')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('basic-authentication-realms/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
