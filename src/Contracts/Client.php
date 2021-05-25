<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Contracts;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\Deployment;

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

    /**
     * Add an affected cluster to the list for deployment.
     *
     * @param int $clusterId
     * @return \Vdhicts\Cyberfusion\ClusterApi\Client
     */
    public function addAffectedCluster(int $clusterId): Client;

    /**
     * Deploy all the affected clusters.
     *
     * @return Deployment[]
     */
    public function deploy(): array;
}
