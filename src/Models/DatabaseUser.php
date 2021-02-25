<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DatabaseUser implements Model
{
    public string $name;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): DatabaseUser
    {
        $databaseUser = new self();
        $databaseUser->name = Arr::get($data, 'name');
        $databaseUser->id = Arr::get($data, 'id');
        $databaseUser->clusterId = Arr::get($data, 'cluster_id');
        $databaseUser->createdAt = Arr::get($data, 'created_at');
        $databaseUser->updatedAt = Arr::get($data, 'updated_at');
        return $databaseUser;
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
