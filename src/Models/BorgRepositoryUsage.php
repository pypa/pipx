<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class BorgRepositoryUsage extends ClusterModel implements Model
{
    private int $borgRepositoryId;
    private int $usage;
    private string $timestamp;

    public function getBorgRepositoryId(): int
    {
        return $this->borgRepositoryId;
    }

    public function setBorgRepositoryId(int $borgRepositoryId): BorgRepositoryUsage
    {
        $this->borgRepositoryId = $borgRepositoryId;

        return $this;
    }

    public function getUsage(): int
    {
        return $this->usage;
    }

    public function setUsage(int $usage): BorgRepositoryUsage
    {
        $this->usage = $usage;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): BorgRepositoryUsage
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function fromArray(array $data): BorgRepositoryUsage
    {
        return $this
            ->setBorgRepositoryId(Arr::get($data, 'unix_user_id'))
            ->setUsage(Arr::get($data, 'usage'))
            ->setTimestamp(Arr::get($data, 'timestamp'));
    }

    public function toArray(): array
    {
        return [
            'borg_repository_id' => $this->getBorgRepositoryId(),
            'usages' => $this->getUsage(),
            'timestamp' => $this->getTimestamp(),
        ];
    }
}
