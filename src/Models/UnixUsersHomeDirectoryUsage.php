<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;

class UnixUsersHomeDirectoryUsage extends ClusterModel implements Model
{
    private int $clusterId;
    private int $usage;
    private string $timestamp;

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): UnixUsersHomeDirectoryUsage
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getUsage(): int
    {
        return $this->usage;
    }

    public function setUsage(int $usage): UnixUsersHomeDirectoryUsage
    {
        $this->usage = $usage;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): UnixUsersHomeDirectoryUsage
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function fromArray(array $data): UnixUsersHomeDirectoryUsage
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
