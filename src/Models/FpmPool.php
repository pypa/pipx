<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class FpmPool extends ClusterModel implements Model
{
    private string $name;
    private int $unixUserId;
    private string $version;
    private int $maxChildren;
    private int $maxRequests = 1000;
    private int $processIdleTimeout = 10;
    private ?int $cpuLimit = null;
    private bool $isNamespaced = false;
    private ?string $unitName = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): FpmPool
    {
        $this->validate($name, [
            'length_max' => 64,
            'pattern' => '^[a-z0-9-_]+$',
        ]);

        $this->name = $name;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): FpmPool
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getVersion(): string
    {
        return $this->version;
    }

    public function setVersion(string $version): FpmPool
    {
        $this->version = $version;

        return $this;
    }

    public function getMaxChildren(): int
    {
        return $this->maxChildren;
    }

    public function setMaxChildren(int $maxChildren): FpmPool
    {
        $this->validate($maxChildren, [
            'positive_integer',
        ]);

        $this->maxChildren = $maxChildren;

        return $this;
    }

    public function getMaxRequests(): int
    {
        return $this->maxRequests;
    }

    public function setMaxRequests(int $maxRequests): FpmPool
    {
        $this->validate($maxRequests, [
            'positive_integer',
        ]);

        $this->maxRequests = $maxRequests;

        return $this;
    }

    public function getProcessIdleTimeout(): int
    {
        return $this->processIdleTimeout;
    }

    public function setProcessIdleTimeout(int $processIdleTimeout): FpmPool
    {
        $this->validate($processIdleTimeout, [
            'positive_integer',
        ]);

        $this->processIdleTimeout = $processIdleTimeout;

        return $this;
    }

    public function getCpuLimit(): ?int
    {
        return $this->cpuLimit;
    }

    public function setCpuLimit(?int $cpuLimit): FpmPool
    {
        $this->validate($cpuLimit, [
            'positive_integer',
        ]);

        $this->cpuLimit = $cpuLimit;

        return $this;
    }

    public function isNamespaced(): bool
    {
        return $this->isNamespaced;
    }

    public function setIsNamespaced(bool $isNamespaced): FpmPool
    {
        $this->isNamespaced = $isNamespaced;

        return $this;
    }

    public function getUnitName(): ?string
    {
        return $this->unitName;
    }

    public function setUnitName(?string $unitName): FpmPool
    {
        $this->unitName = $unitName;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): FpmPool
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): FpmPool
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): FpmPool
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): FpmPool
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): FpmPool
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setVersion(Arr::get($data, 'version'))
            ->setMaxChildren(Arr::get($data, 'max_children'))
            ->setMaxRequests(Arr::get($data, 'max_requests'))
            ->setProcessIdleTimeout(Arr::get($data, 'process_idle_timeout'))
            ->setCpuLimit(Arr::get($data, 'cpu_limit'))
            ->setIsNamespaced((bool)Arr::get($data, 'is_namespaced'))
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
            'unix_user_id' => $this->getUnixUserId(),
            'version' => $this->getVersion(),
            'max_children' => $this->getMaxChildren(),
            'max_requests' => $this->getMaxRequests(),
            'process_idle_timeout' => $this->getProcessIdleTimeout(),
            'cpu_limit' => $this->getCpuLimit(),
            'is_namespaced' => $this->isNamespaced(),
            'unit_name' => $this->getUnitName(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
