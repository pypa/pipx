<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DatabaseUserGrant extends ClusterModel implements Model
{
    public const DEFAULT_PRIVILEGE_NAME = 'ALL';

    private int $databaseId;
    private int $databaseUserId;
    private ?string $tableName = null;
    private string $privilegeName = self::DEFAULT_PRIVILEGE_NAME;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getDatabaseId(): int
    {
        return $this->databaseId;
    }

    public function setDatabaseId(int $databaseId): DatabaseUserGrant
    {
        $this->databaseId = $databaseId;

        return $this;
    }

    public function getDatabaseUserId(): int
    {
        return $this->databaseUserId;
    }

    public function setDatabaseUserId(int $databaseUserId): DatabaseUserGrant
    {
        $this->databaseUserId = $databaseUserId;

        return $this;
    }

    public function getTableName(): ?string
    {
        return $this->tableName;
    }

    public function setTableName(?string $tableName = null): DatabaseUserGrant
    {
        $this->validate($tableName, [
            'length_max' => 64,
            'pattern' => '^[a-z0-9-_]+$',
            'nullable' => true,
        ]);

        $this->tableName = $tableName;

        return $this;
    }

    public function getPrivilegeName(): string
    {
        return $this->privilegeName;
    }

    public function setPrivilegeName(string $privilegeName): DatabaseUserGrant
    {
        $this->privilegeName = $privilegeName;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): DatabaseUserGrant
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): DatabaseUserGrant
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): DatabaseUserGrant
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): DatabaseUserGrant
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): DatabaseUserGrant
    {
        return $this
            ->setDatabaseId(Arr::get($data, 'database_id'))
            ->setDatabaseUserId(Arr::get($data, 'database_user_id'))
            ->setTableName(Arr::get($data, 'table_name'))
            ->setPrivilegeName(Arr::get($data,'privilege_name',self::DEFAULT_PRIVILEGE_NAME))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'database_id' => $this->getDatabaseId(),
            'database_user_id' => $this->getDatabaseUserId(),
            'table_name' => $this->getTableName(),
            'privilege_name' => $this->getPrivilegeName(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
