<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;

class RedisInstance extends ClusterModel implements Model
{
    private string $name;
    private string $password;
    private int $maxDatabases = 16;
    private ?int $port = null;
    private int $memoryLimit = 100;
    private int $primaryNodeId;
    private ?string $unitName = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): RedisInstance
    {
        Validator::value($name)
            ->maxLength(64)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): RedisInstance
    {
        Validator::value($password)
            ->minLength(24)
            ->maxLength(255)
            ->pattern('^[a-zA-Z0-9]+$')
            ->validate();

        $this->password = $password;

        return $this;
    }

    public function getMaxDatabases(): int
    {
        return $this->maxDatabases;
    }

    public function setMaxDatabases(int $maxDatabases): RedisInstance
    {
        $this->maxDatabases = $maxDatabases;

        return $this;
    }

    public function getPort(): ?int
    {
        return $this->port;
    }

    public function setPort(?int $port): RedisInstance
    {
        $this->port = $port;

        return $this;
    }

    public function getMemoryLimit(): int
    {
        return $this->memoryLimit;
    }

    public function setMemoryLimit(int $memoryLimit): RedisInstance
    {
        $this->memoryLimit = $memoryLimit;

        return $this;
    }

    public function getPrimaryNodeId(): int
    {
        return $this->primaryNodeId;
    }

    public function setPrimaryNodeId(int $primaryNodeId): RedisInstance
    {
        $this->primaryNodeId = $primaryNodeId;

        return $this;
    }

    public function getUnitName(): ?string
    {
        return $this->unitName;
    }

    public function setUnitName(?string $unitName): RedisInstance
    {
        $this->unitName = $unitName;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): RedisInstance
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): RedisInstance
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): RedisInstance
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): RedisInstance
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): RedisInstance
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setPassword(Arr::get($data, 'password'))
            ->setMaxDatabases(Arr::get($data, 'max_databases'))
            ->setPort(Arr::get($data, 'port'))
            ->setMemoryLimit(Arr::get($data, 'memory_limit'))
            ->setPrimaryNodeId(Arr::get($data, 'primary_node_id'))
            ->setUnitName(Arr::get($data, 'unit_name'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'password' => $this->getPassword(),
            'max_databases' => $this->getMaxDatabases(),
            'port' => $this->getPort(),
            'memory_limit' => $this->getMemoryLimit(),
            'primary_node_id' => $this->getPrimaryNodeId(),
            'unit_name' => $this->getUnitName(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
