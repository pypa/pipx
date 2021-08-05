<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\Cron;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class Crons extends Endpoint
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
            ->setUrl(sprintf('crons?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'crons' => array_map(
                function (array $data) {
                    return (new Cron())->fromArray($data);
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
     * @param Cron $cron
     * @return Response
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
            ->setBody($this->filterFields($cron->toArray(), [
                'name',
                'command',
                'email_address',
                'schedule',
                'unix_user_id',
                'error_count',
                'locking_enabled',
                'is_active',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cron = (new Cron())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($cron->getClusterId());

        return $response->setData([
            'cron' => $cron,
        ]);
    }

    /**
     * @param Cron $cron
     * @return Response
     * @throws RequestException
     */
    public function update(Cron $cron): Response
    {
        $this->validateRequired($cron, 'update', [
            'name',
            'command',
            'schedule',
            'unix_user_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('crons/%d', $cron->getId()))
            ->setBody($this->filterFields($cron->toArray(), [
                'name',
                'command',
                'email_address',
                'schedule',
                'unix_user_id',
                'error_count',
                'locking_enabled',
                'is_active',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cron = (new Cron())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($cron->getClusterId());

        return $response->setData([
            'cron' => $cron,
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
                ->getData('cron')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('crons/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
