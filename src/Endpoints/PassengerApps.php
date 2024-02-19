<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\PassengerApp;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Support\Str;

class PassengerApps extends Endpoint
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
            ->setUrl(sprintf('passenger-apps?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'passengerApps' => array_map(
                fn (array $data) => (new PassengerApp())->fromArray($data),
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
            ->setBody(
                $this->filterFields($passengerApp->toArray(), [
                    'name',
                    'unix_user_id',
                    'environment',
                    'environment_variables',
                    'max_pool_size',
                    'max_requests',
                    'pool_idle_time',
                    'nodejs_version',
                    'startup_file',
                    'is_namespaced',
                    'cpu_limit',
                    'app_root',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $passengerApp = (new PassengerApp())->fromArray($response->getData());

        return $response->setData([
            'passengerApp' => $passengerApp,
        ]);
    }

    /**
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
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('passenger-apps/%d', $passengerApp->getId()))
            ->setBody(
                $this->filterFields($passengerApp->toArray(), [
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
                    'is_namespaced',
                    'cpu_limit',
                    'app_root',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $passengerApp = (new PassengerApp())->fromArray($response->getData());

        return $response->setData([
            'passengerApp' => $passengerApp,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('passenger-app/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function restart(int $id, ?string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('passenger-apps/%d/restart', $id),
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
