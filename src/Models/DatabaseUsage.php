<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DatabaseUsage extends ClusterModel implements Model
{
    private int $databaseId;
    private int $usage;
    private string $timestamp;

    public function getDatabaseId(): int
    {
        return $this->databaseId;
    }

    public function setDatabaseId(int $databaseId): DatabaseUsage
    {
        $this->databaseId = $databaseId;

        return $this;
    }

    public function getUsage(): int
    {
        return $this->usage;
    }

    public function setUsage(int $usage): DatabaseUsage
    {
        $this->usage = $usage;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): DatabaseUsage
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function fromArray(array $data): DatabaseUsage
    {
        return $this
            ->setDatabaseId(Arr::get($data, 'database_id'))
            ->setUsage(Arr::get($data, 'usage'))
            ->setTimestamp(Arr::get($data, 'timestamp'));
    }

    public function toArray(): array
    {
        return [
            'database_id' => $this->getDatabaseId(),
            'usage' => $this->getUsage(),
            'timestamp' => $this->getTimestamp(),
        ];
    }
}
