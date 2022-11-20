<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;

class UnixUsersHomeDirectoryUsage extends ClusterModel implements Model
{
    private int $clusterId;
    private int $usage;
    private string $timestamp;

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): self
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getUsage(): int
    {
        return $this->usage;
    }

    public function setUsage(int $usage): self
    {
        $this->usage = $usage;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): self
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setUsage(Arr::get($data, 'usage'))
            ->setTimestamp(Arr::get($data, 'timestamp'));
    }

    public function toArray(): array
    {
        return [
            'cluster_id' => $this->getClusterId(),
            'usage' => $this->getUsage(),
            'timestamp' => $this->getTimestamp(),
        ];
    }
}
