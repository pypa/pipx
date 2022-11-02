<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\VirtualHost;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Support\Str;

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
        $this->validateRequired($virtualHost, 'create', [
            'domain',
            'server_aliases',
            'unix_user_id',
            'document_root',
            'public_root',
            'force_ssl',
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
                'passenger_app_id',
                'force_ssl',
                'custom_config',
                'server_software_name',
                'allow_override_directives',
                'allow_override_option_directives',
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
            'id',
            'server_software_name',
            'domain_root',
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
                'passenger_app_id',
                'force_ssl',
                'custom_config',
                'id',
                'server_software_name',
                'allow_override_directives',
                'allow_override_option_directives',
                'domain_root',
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

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function documentRootFiles(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('virtual-hosts/%d/document-root', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'files' => $response->getData('contains_files'),
        ]);
    }

    /**
     * @param int $leftVirtualHostId
     * @param int $rightVirtualHostId
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function syncDomainRootTo(int $leftVirtualHostId, int $rightVirtualHostId, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('virtual-hosts/%d/domain-root/sync?right_virtual_host_id=%d',
                $leftVirtualHostId,
                $rightVirtualHostId
            ),
            ['callback_url' => $callbackUrl]
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $taskCollection = (new TaskCollection())->fromArray($response->getData());

        return $response->setData([
            'taskCollection' => $taskCollection,
        ]);
    }
}
