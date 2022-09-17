<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\TaskResult;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;

class TaskCollections extends Endpoint
{
    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function results(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('task-collections/%d/results', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'taskResults' => array_map(
                function (array $data) {
                    return (new TaskResult())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }
}
