<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Cluster implements Model
{
    public string $name;
    public ?string $group = null;
    public ?int $id = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Cluster
    {
        $cluster = new self();
        $cluster->name = Arr::get($data, 'name');
        $cluster->group = Arr::get($data, 'group');
        $cluster->id = Arr::get($data, 'id');
        $cluster->createdAt = Arr::get($data, 'created_at');
        $cluster->updatedAt = Arr::get($data, 'updated_at');
        return $cluster;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'group' => $this->group,
            'id' => $this->id,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
