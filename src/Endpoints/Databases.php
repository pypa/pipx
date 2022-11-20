<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Enums\TimeUnit;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Database;
use Cyberfusion\ClusterApi\Models\DatabaseComparison;
use Cyberfusion\ClusterApi\Models\DatabaseUsage;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Support\Str;
use DateTimeInterface;

class Databases extends Endpoint
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
            ->setUrl(sprintf('databases?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databases' => array_map(
                function (array $data) {
                    return (new Database())->fromArray($data);
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
            ->setUrl(sprintf('databases/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'database' => (new Database())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param Database $database
     * @return Response
     * @throws RequestException
     */
    public function create(Database $database): Response
    {
        $this->validateRequired($database, 'create', [
            'name',
            'server_software_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('databases')
            ->setBody($this->filterFields($database->toArray(), [
                'name',
                'server_software_name',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $database = (new Database())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($database->getClusterId());

        return $response->setData([
            'database' => $database,
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
                ->getData('database')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('databases/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @param int $id
     * @param DateTimeInterface $from
     * @param string $timeUnit
     * @return Response
     * @throws RequestException
     */
    public function usages(int $id, DateTimeInterface $from, string $timeUnit = TimeUnit::HOURLY): Response
    {
        $url = sprintf(
            'databases/usages/%d?%s',
            $id,
            http_build_query([
                'timestamp' => $from->format('c'),
                'time_unit' => $timeUnit,
            ])
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUsage' => count($response->getData()) !== 0
                ? array_map(
                    function (array $data) {
                        return (new DatabaseUsage())->fromArray($data);
                    },
                    $response->getData()
                )
                : null,
        ]);
    }

    /**
     * @param int $leftDatabaseId
     * @param int $rightDatabaseId
     * @return Response
     * @throws RequestException
     */
    public function compareTo(int $leftDatabaseId, int $rightDatabaseId): Response
    {
        $url = sprintf(
            'databases/%d/comparison?right_database_id=%d',
            $leftDatabaseId,
            $rightDatabaseId
        );

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl($url);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseComparison' => (new DatabaseComparison())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param int $leftDatabaseId
     * @param int $rightDatabaseId
     * @param string|null $callbackUrl
     * @return Response
     * @throws RequestException
     */
    public function syncTo(int $leftDatabaseId, int $rightDatabaseId, string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf(
                'databases/%d/sync?right_database_id=%d',
                $leftDatabaseId,
                $rightDatabaseId
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
