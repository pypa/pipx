<?php

namespace Cyberfusion\ClusterApi\Support;

use Cyberfusion\ClusterApi\Models\Cluster;
use Cyberfusion\ClusterApi\Models\DetailMessage;
use Cyberfusion\ClusterApi\Models\HttpValidationError;

class Deployment
{
    private int $clusterId;
    private bool $success = false;
    private ?Cluster $cluster = null;
    /** @var DetailMessage|HttpValidationError|string */
    private $error = null;

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): self
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function isSuccess(): bool
    {
        return $this->success;
    }

    public function setSuccess(bool $success): self
    {
        $this->success = $success;

        return $this;
    }

    public function getCluster(): ?Cluster
    {
        return $this->cluster;
    }

    public function setCluster(?Cluster $cluster): self
    {
        $this->cluster = $cluster;

        return $this;
    }

    /**
     * @return string|DetailMessage|HttpValidationError|null
     */
    public function getError()
    {
        return $this->error;
    }

    /**
     * @param string|DetailMessage|HttpValidationError|null $error
     * @return $this
     */
    public function setError($error): self
    {
        $this->error = $error;

        return $this;
    }
}
