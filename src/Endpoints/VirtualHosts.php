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
            ->setUrl(sprintf('virtual-hosts?%s', http_build_query($filter->toArray())));

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
     * @return Response
     * @throws RequestException
     */
    public function get(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('virtual-hosts/%d', $id));

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
        $requiredAttributes = [
            'domain',
            'serverAliases',
            'unixUserId',
            'documentRoot',
            'publicRoot',
            'forceSsl',
            'balancerBackendName',
        ];
        $this->validateRequired($virtualHost, 'create', $requiredAttributes);

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

        return $response->setData([
            'virtualHost' => (new VirtualHost())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param VirtualHost $virtualHost
     * @return Response
     * @throws RequestException
     */
    public function update(VirtualHost $virtualHost): Response
    {
        $requiredAttributes = [
            'domain',
            'serverAliases',
            'unixUserId',
            'documentRoot',
            'publicRoot',
            'forceSsl',
            'id',
            'clusterId',
            'balancerBackendName',
        ];
        $this->validateRequired($virtualHost, 'update', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('virtual-hosts/%d', $virtualHost->id))
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

        return $response->setData([
            'virtualHost' => (new VirtualHost())->fromArray($response->getData()),
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
            ->setUrl(sprintf('virtual-hosts/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
