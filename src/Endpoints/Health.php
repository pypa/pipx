<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Health as HealthModel;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;

class Health extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function get(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl('health')
            ->setAuthenticationRequired(false);

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'health' => (new HealthModel())->fromArray($response->getData()),
        ]);
    }
}
