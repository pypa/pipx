<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Cron;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class Crons extends Endpoint
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
            ->setUrl(sprintf('crons?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'crons' => array_map(
                fn (array $data) => (new Cron())->fromArray($data),
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
            ->setUrl(sprintf('crons/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cron' => (new Cron())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(Cron $cron): Response
    {
        $this->validateRequired($cron, 'create', [
            'name',
            'command',
            'schedule',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('crons')
            ->setBody(
                $this->filterFields($cron->toArray(), [
                    'name',
                    'command',
                    'email_address',
                    'schedule',
                    'unix_user_id',
                    'node_id',
                    'error_count',
                    'random_delay_max_seconds',
                    'timeout_seconds',
                    'locking_enabled',
                    'is_active',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cron = (new Cron())->fromArray($response->getData());

        return $response->setData([
            'cron' => $cron,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(Cron $cron): Response
    {
        $this->validateRequired($cron, 'update', [
            'name',
            'command',
            'schedule',
            'unix_user_id',
            'node_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('crons/%d', $cron->getId()))
            ->setBody(
                $this->filterFields($cron->toArray(), [
                    'name',
                    'command',
                    'email_address',
                    'schedule',
                    'unix_user_id',
                    'node_id',
                    'error_count',
                    'random_delay_max_seconds',
                    'timeout_seconds',
                    'locking_enabled',
                    'is_active',
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

        $cron = (new Cron())->fromArray($response->getData());

        return $response->setData([
            'cron' => $cron,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('crons/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
