<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Database implements Model
{
    public const SERVER_SOFTWARE_MARIADB = 'MariaDB';
    public const SERVER_SOFTWARE_POSTGRES = 'PostgreSQL';

    public const DEFAULT_SERVER_SOFTWARE = self::SERVER_SOFTWARE_MARIADB;

    public string $name;
    public string $serverSoftwareName = self::DEFAULT_SERVER_SOFTWARE;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Database
    {
        $database = new self();
        $database->name = Arr::get($data, 'name');
        $database->serverSoftwareName = Arr::get(
            $data,
            'server_software_name',
            self::DEFAULT_SERVER_SOFTWARE
        );
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
            'server_software_name' => $this->serverSoftwareName,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
