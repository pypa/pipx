<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\HostsEntry;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class HostsEntries extends Endpoint
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
            ->setUrl(sprintf('hosts-entries?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'hostsEntries' => array_map(
                fn (array $data) => (new HostsEntry())->fromArray($data),
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
            ->setUrl(sprintf('hosts-entries/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'hostsEntry' => (new HostsEntry())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(HostsEntry $hostsEntry): Response
    {
        $this->validateRequired($hostsEntry, 'create', [
            'node_id',
            'host_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('hosts-entries')
            ->setBody(
                $this->filterFields($hostsEntry->toArray(), [
                    'node_id',
                    'host_name',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $hostsEntry = (new HostsEntry())->fromArray($response->getData());

        return $response->setData([
            'hostsEntry' => $hostsEntry,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('hosts-entries/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
