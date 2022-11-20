<?php

namespace Cyberfusion\ClusterApi\Contracts;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\Deployment;

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
     * @return \Cyberfusion\ClusterApi\Client
     */
    public function addAffectedCluster(int $clusterId): self;

    /**
     * Deploy all the affected clusters.
     *
     * @return Deployment[]
     */
    public function deploy(): array;
}
