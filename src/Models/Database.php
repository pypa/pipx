<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Database implements Model
{
    public string $name;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Database
    {
        $database = new self();
        $database->name = Arr::get($data, 'name');
        $database->id = Arr::get($data, 'id');
        $database->clusterId = Arr::get($data, 'cluster_id');
        $database->createdAt = Arr::get($data, 'created_at');
        $database->updatedAt = Arr::get($data, 'updated_at');
        return $database;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
