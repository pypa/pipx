<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DatabaseUser implements Model
{
    private const DEFAULT_HOST = '%';

    public string $name;
    public string $host = self::DEFAULT_HOST;
    public string $password = '';
    public string $serverSoftwareName = Database::DEFAULT_SERVER_SOFTWARE;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): DatabaseUser
    {
        $databaseUser = new self();
        $databaseUser->name = Arr::get($data, 'name');
        $databaseUser->id = Arr::get($data, 'id');
        $databaseUser->host = Arr::get($data, 'host', self::DEFAULT_HOST);
        $databaseUser->serverSoftwareName = Arr::get(
            $data,
            'server_software_name',
            Database::DEFAULT_SERVER_SOFTWARE
        );
        $databaseUser->clusterId = Arr::get($data, 'cluster_id');
        $databaseUser->createdAt = Arr::get($data, 'created_at');
        $databaseUser->updatedAt = Arr::get($data, 'updated_at');
        return $databaseUser;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'host' => $this->host,
            'password' => $this->password,
            'server_software_name' => $this->serverSoftwareName,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
