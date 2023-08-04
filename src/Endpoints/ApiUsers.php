<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;

class ApiUsers extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function clustersChildren(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl('api-users/clusters-children');

        return $this
            ->client
            ->request($request);
    }
}
