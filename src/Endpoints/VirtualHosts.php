<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\VirtualHost;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class VirtualHosts extends Endpoint
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
            ->setUrl(sprintf('virtual-hosts?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'virtualHosts' => array_map(
                function (array $data) {
                    return (new VirtualHost())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }

    /**
     * @param int $id
     * @param bool $documentRootContainsFiles
     * @return Response
     * @throws RequestException
     */
    public function get(int $id, bool $documentRootContainsFiles = false): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf(
                'virtual-hosts/%d?%s',
                $id,
                http_build_query(['get_document_root_contains_files' => $documentRootContainsFiles])
            ));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'virtualHost' => (new VirtualHost())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param VirtualHost $virtualHost
     * @return Response
     * @throws RequestException
     */
    public function create(VirtualHost $virtualHost): Response
    {
        $this->validateRequired($virtualHost, 'create', [
            'domain',
            'server_aliases',
            'unix_user_id',
            'document_root',
            'public_root',
            'force_ssl',
            'balancer_backend_name',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('virtual-hosts')
            ->setBody($this->filterFields($virtualHost->toArray(), [
                'domain',
                'server_aliases',
                'unix_user_id',
                'document_root',
                'public_root',
                'fpm_pool_id',
                'force_ssl',
                'custom_config',
                'balancer_backend_name',
                'deploy_commands',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        $virtualHost = (new VirtualHost())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($virtualHost->getClusterId());

        return $response->setData([
            'virtualHost' => $virtualHost,
        ]);
    }

    /**
     * @param VirtualHost $virtualHost
     * @return Response
     * @throws RequestException
     */
    public function update(VirtualHost $virtualHost): Response
    {
        $this->validateRequired($virtualHost, 'update', [
            'domain',
            'server_aliases',
            'unix_user_id',
            'document_root',
            'public_root',
            'force_ssl',
            'balancer_backend_name',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('virtual-hosts/%d', $virtualHost->getId()))
            ->setBody($this->filterFields($virtualHost->toArray(), [
                'domain',
                'server_aliases',
                'unix_user_id',
                'document_root',
                'public_root',
                'fpm_pool_id',
                'force_ssl',
                'custom_config',
                'balancer_backend_name',
                'deploy_commands',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        $virtualHost = (new VirtualHost())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($virtualHost->getClusterId());

        return $response->setData([
            'virtualHost' => $virtualHost,
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
                ->getData('virtualHost')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('virtual-hosts/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
