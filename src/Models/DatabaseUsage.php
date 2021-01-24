<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DatabaseUsage implements Model
{
    public int $databaseId;
    public int $usage;
    public string $timestamp;

    public function fromArray(array $data): DatabaseUsage
    {
        $databaseUsage = new self();
        $databaseUsage->databaseId = Arr::get($data, 'database_id');
        $databaseUsage->usage = Arr::get($data, 'usage');
        $databaseUsage->timestamp = Arr::get($data, 'timestamp');
        return $databaseUsage;
    }

    public function toArray(): array
    {
        return [
            'database_id' => $this->databaseId,
            'usage' => $this->usage,
            'timestamp' => $this->timestamp,
        ];
    }
}
