<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\RedisInstanceEvictionPolicy;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class RedisInstance extends ClusterModel
{
    private string $name;
    private string $password;
    private int $maxDatabases = 16;
    private ?int $port = null;
    private int $memoryLimit = 100;
    private string $evictionPolicy;
    private int $primaryNodeId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): self
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

    public function setPassword(string $password): self
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

    public function setMaxDatabases(int $maxDatabases): self
    {
        $this->maxDatabases = $maxDatabases;

        return $this;
    }

    public function getPort(): ?int
    {
        return $this->port;
    }

    public function setPort(?int $port): self
    {
        $this->port = $port;

        return $this;
    }

    public function getMemoryLimit(): int
    {
        return $this->memoryLimit;
    }

    public function setMemoryLimit(int $memoryLimit): self
    {
        $this->memoryLimit = $memoryLimit;

        return $this;
    }

    public function getEvictionPolicy(): string
    {
        return $this->evictionPolicy;
    }

    public function setEvictionPolicy(string $evictionPolicy): self
    {
        Validator::value($evictionPolicy)
            ->valueIn(RedisInstanceEvictionPolicy::AVAILABLE)
            ->validate();

        $this->evictionPolicy = $evictionPolicy;

        return $this;
    }

    public function getPrimaryNodeId(): int
    {
        return $this->primaryNodeId;
    }

    public function setPrimaryNodeId(int $primaryNodeId): self
    {
        $this->primaryNodeId = $primaryNodeId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): self
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): self
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): self
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): self
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setPassword(Arr::get($data, 'password'))
            ->setMaxDatabases(Arr::get($data, 'max_databases'))
            ->setPort(Arr::get($data, 'port'))
            ->setMemoryLimit(Arr::get($data, 'memory_limit'))
            ->setEvictionPolicy(Arr::get($data, 'eviction_policy'))
            ->setPrimaryNodeId(Arr::get($data, 'primary_node_id'))
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
            'eviction_policy' => $this->getEvictionPolicy(),
            'primary_node_id' => $this->getPrimaryNodeId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
