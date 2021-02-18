<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\Health as HealthModel;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;

class Health extends Endpoint
{
    /**
     * @return Response
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
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'health' => (new HealthModel())->fromArray($response->getData()),
        ]);
    }
}
