<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Contracts;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;

interface Client
{
    /**
     * @param Request $request
     * @return Response
     * @throws RequestException
     */
    public function request(Request $request): Response;

    public function addAffectedCluster(int $clusterId): Client;
}
