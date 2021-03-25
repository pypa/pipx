<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\DatabaseUserGrant;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class DatabaseUserGrants extends Endpoint
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
            ->setUrl(sprintf('database-user-grants?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUserGrants' => array_map(
                function (array $data) {
                    return (new DatabaseUserGrant())->fromArray($data);
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
            ->setUrl(sprintf('database-user-grants/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUserGrant' => (new DatabaseUserGrant())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param DatabaseUserGrant $databaseUserGrant
     * @return Response
     * @throws RequestException
     */
    public function create(DatabaseUserGrant $databaseUserGrant): Response
    {
        $requiredAttributes = [
            'databaseId',
            'databaseUserId',
            'tableName',
            'privilegeName',
        ];
        $this->validateRequired($databaseUserGrant, 'create', $requiredAttributes);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('database-user-grants')
            ->setBody($this->filterFields($databaseUserGrant->toArray(), [
                'database_id',
                'database_user_id',
                'table_name',
                'privilege_name',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'databaseUserGrant' => (new DatabaseUserGrant())->fromArray($response->getData()),
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
            ->setUrl(sprintf('database-user-grants/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
