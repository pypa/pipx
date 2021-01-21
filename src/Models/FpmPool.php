<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class FpmPool implements Model
{
    public string $name;
    public int $unixUserId;
    public string $version;
    public int $maxChildren;
    public int $maxRequests = 1000;
    public int $processIdleTimeout = 600;
    public ?int $cpuLimit = null;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): FpmPool
    {
        $fpmPool = new FpmPool();
        $fpmPool->name = Arr::get($data, 'name');
        $fpmPool->unixUserId = Arr::get($data, 'unix_user_id');
        $fpmPool->version = Arr::get($data, 'version');
        $fpmPool->maxChildren = Arr::get($data, 'max_children');
        $fpmPool->maxRequests = Arr::get($data, 'max_requests');
        $fpmPool->processIdleTimeout = Arr::get($data, 'process_idle_timeout');
        $fpmPool->cpuLimit = Arr::get($data, 'cpu_limit');
        $fpmPool->id = Arr::get($data, 'id');
        $fpmPool->clusterId = Arr::get($data, 'cluster_id');
        $fpmPool->createdAt = Arr::get($data, 'created_at');
        $fpmPool->updatedAt = Arr::get($data, 'updated_at');
        return $fpmPool;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'unix_user_id' => $this->unixUserId,
            'version' => $this->version,
            'max_children' => $this->maxChildren,
            'max_requests' => $this->maxRequests,
            'process_idle_timeout' => $this->processIdleTimeout,
            'cpu_limit' => $this->cpuLimit,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
