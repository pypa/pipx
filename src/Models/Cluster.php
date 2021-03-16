<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Cluster implements Model
{
    public string $name = '';
    public ?array $groups = [];
    public ?string $unixUsersHomeDirectory = null;
    public ?string $databasesDataDirectory = null;
    public ?int $id = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Cluster
    {
        $cluster = new self();
        $cluster->name = Arr::get($data, 'name');
        $cluster->groups = Arr::get($data, 'groups', []);
        $cluster->unixUsersHomeDirectory = Arr::get($data, 'unix_users_home_directory');
        $cluster->databasesDataDirectory = Arr::get($data, 'databases_data_directory');
        $cluster->id = Arr::get($data, 'id');
        $cluster->createdAt = Arr::get($data, 'created_at');
        $cluster->updatedAt = Arr::get($data, 'updated_at');
        return $cluster;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'groups' => $this->groups,
            'unix_users_home_directory' => $this->unixUsersHomeDirectory,
            'databases_data_directory' => $this->databasesDataDirectory,
            'id' => $this->id,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
