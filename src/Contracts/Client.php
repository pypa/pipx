<?php

namespace Cyberfusion\ClusterApi\Contracts;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;

interface Client
{
    /**
     * Performs the request.
     *
     * @param Request $request
     * @return Response
     * @throws RequestException
     */
    public function request(Request $request): Response;
}
