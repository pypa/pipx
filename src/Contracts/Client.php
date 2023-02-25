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
     * @throws RequestException
     */
    public function request(Request $request): Response;
}
