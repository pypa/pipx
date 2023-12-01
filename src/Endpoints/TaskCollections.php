<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Models\TaskResult;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\Str;

class TaskCollections extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function results(string $uuid): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('task-collections/%s/results', $uuid));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'taskResults' => array_map(
                fn (array $data) => (new TaskResult())->fromArray($data),
                $response->getData()
            ),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function retry(string $uuid, ?string $callbackUrl = null): Response
    {
        $url = Str::optionalQueryParameters(
            sprintf('task-collections/%s/retry', $uuid),
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

        return $response->setData([
            'taskCollection' => (new TaskCollection())->fromArray($response->getData()),
        ]);
    }
}
