<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\PassengerApp;
use Vdhicts\Cyberfusion\ClusterApi\Models\TaskCollection;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;
use Vdhicts\Cyberfusion\ClusterApi\Support\Str;

class PassengerApps extends Endpoint
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
            ->setUrl(sprintf('passenger-apps?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'passengerApps' => array_map(
                function (array $data) {
                    return (new PassengerApp())->fromArray($data);
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
            ->setUrl(sprintf('passenger-apps/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'passengerApp' => (new PassengerApp())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param PassengerApp $passengerApp
     * @return Response
     * @throws RequestException
     */
    public function createNodejs(PassengerApp $passengerApp): Response
    {
        $this->validateRequired($passengerApp, 'create', [
            'name',
            'unix_user_id',
            'environment',
            'nodejs_version',
            'startup_file',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('passenger-apps/nodejs')
            ->setBody($this->filterFields($passengerApp->toArray(), [
                'name',
                'unix_user_id',
                'environment',
                'environment_variables',
                'max_pool_size',
                'max_requests',
                'pool_idle_time',
                'nodejs_version',
                'startup_file',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $passengerApp = (new PassengerApp())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($passengerApp->getClusterId());

        return $response->setData([
            'passengerApp' => $passengerApp,
        ]);
    }

    /**
     * @param PassengerApp $passengerApp
     * @return Response
     * @throws RequestException
     */
    public function update(PassengerApp $passengerApp): Response
    {
        $this->validateRequired($passengerApp, 'update', [
            'name',
            'unix_user_id',
            'environment',
            'id',
            'cluster_id',
            'port',
            'app_type',
            'startup_file',
            'unit_name',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('passenger-apps/%d', $passengerApp->getId()))
            ->setBody($this->filterFields($passengerApp->toArray(), [
                'name',
                'unix_user_id',
                'environment',
                'environment_variables',
                'max_pool_size',
                'max_requests',
                'pool_idle_time',
                'id',
                'cluster_id',
                'port',
                'app_type',
                'nodejs_version',
                'startup_file',
                'unit_name',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $passengerApp = (new PassengerApp())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($passengerApp->getClusterId());

        return $response->setData([
            'passengerApp' => $passengerApp,
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
                ->getData('passengerApp')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('passenger-app/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function restart(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('passenger-apps/%d/restart', $id));

        return $this
            ->client
            ->request($request);
    }
}
