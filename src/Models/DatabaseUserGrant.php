<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DatabaseUserGrant implements Model
{
    public const DEFAULT_TABLE_NAME = '*';
    public const DEFAULT_PRIVILEGE_NAME = 'ALL';

    public int $databaseId;
    public int $databaseUserId;
    public string $tableName = self::DEFAULT_TABLE_NAME;
    public string $privilegeName = self::DEFAULT_PRIVILEGE_NAME;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): DatabaseUserGrant
    {
        $databaseUserGrant = new self();
        $databaseUserGrant->databaseId = Arr::get($data, 'database_id');
        $databaseUserGrant->databaseUserId = Arr::get($data, 'database_user_id');
        $databaseUserGrant->tableName = Arr::get($data, 'table_name', self::DEFAULT_TABLE_NAME);
        $databaseUserGrant->privilegeName = Arr::get($data,'privilege_name',self::DEFAULT_PRIVILEGE_NAME);
        $databaseUserGrant->id = Arr::get($data, 'id');
        $databaseUserGrant->clusterId = Arr::get($data, 'cluster_id');
        $databaseUserGrant->createdAt = Arr::get($data, 'created_at');
        $databaseUserGrant->updatedAt = Arr::get($data, 'updated_at');
        return $databaseUserGrant;
    }

    public function toArray(): array
    {
        return [
            'database_id' => $this->databaseId,
            'database_user_id' => $this->databaseUserId,
            'table_name' => $this->tableName,
            'privilege_name' => $this->privilegeName,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
