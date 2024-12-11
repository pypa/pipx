<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class FpmPool extends ClusterModel
{
    private string $name;
    private int $unixUserId;
    private string $version;
    private int $maxChildren;
    private int $maxRequests = 1000;
    private int $processIdleTimeout = 10;
    private ?int $cpuLimit = null;
    private ?int $memoryLimit = null;
    private ?int $logShowRequestsThreshold = null;
    private bool $isNamespaced = false;
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

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): self
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getVersion(): string
    {
        return $this->version;
    }

    public function setVersion(string $version): self
    {
        $this->version = $version;

        return $this;
    }

    public function getMaxChildren(): int
    {
        return $this->maxChildren;
    }

    public function setMaxChildren(int $maxChildren): self
    {
        $this->maxChildren = $maxChildren;

        return $this;
    }

    public function getMaxRequests(): int
    {
        return $this->maxRequests;
    }

    public function setMaxRequests(int $maxRequests): self
    {
        $this->maxRequests = $maxRequests;

        return $this;
    }

    public function getProcessIdleTimeout(): int
    {
        return $this->processIdleTimeout;
    }

    public function setProcessIdleTimeout(int $processIdleTimeout): self
    {
        $this->processIdleTimeout = $processIdleTimeout;

        return $this;
    }

    public function getCpuLimit(): ?int
    {
        return $this->cpuLimit;
    }

    public function setCpuLimit(?int $cpuLimit): self
    {
        $this->cpuLimit = $cpuLimit;

        return $this;
    }

    public function getMemoryLimit(): ?int
    {
        return $this->memoryLimit;
    }

    public function setMemoryLimit(?int $memoryLimit): self
    {
        $this->memoryLimit = $memoryLimit;

        return $this;
    }

    public function getLogShowRequestsThreshold(): ?int
    {
        return $this->logShowRequestsThreshold;
    }

    public function setLogShowRequestsThreshold(?int $logShowRequestsThreshold): self
    {
        $this->logShowRequestsThreshold = $logShowRequestsThreshold;

        return $this;
    }

    public function isNamespaced(): bool
    {
        return $this->isNamespaced;
    }

    public function setIsNamespaced(bool $isNamespaced): self
    {
        $this->isNamespaced = $isNamespaced;

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
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setVersion(Arr::get($data, 'version'))
            ->setMaxChildren(Arr::get($data, 'max_children'))
            ->setMaxRequests(Arr::get($data, 'max_requests'))
            ->setProcessIdleTimeout(Arr::get($data, 'process_idle_timeout'))
            ->setCpuLimit(Arr::get($data, 'cpu_limit'))
            ->setMemoryLimit(Arr::get($data, 'memory_limit'))
            ->setLogShowRequestsThreshold(Arr::get($data, 'log_slow_requests_threshold'))
            ->setIsNamespaced((bool)Arr::get($data, 'is_namespaced'))
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
            'memory_limit' => $this->getMemoryLimit(),
            'log_slow_requests_threshold' => $this->getLogShowRequestsThreshold(),
            'is_namespaced' => $this->isNamespaced(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
