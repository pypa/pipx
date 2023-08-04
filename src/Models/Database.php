<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\DatabaseEngine;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class Database extends ClusterModel
{
    private string $name;
    private string $serverSoftwareName = DatabaseEngine::SERVER_SOFTWARE_MARIADB;
    private ?bool $optimizingEnabled = null;
    private ?bool $backupsEnabled = null;
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
            ->maxLength(63)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getServerSoftwareName(): string
    {
        return $this->serverSoftwareName;
    }

    public function setServerSoftwareName(string $serverSoftwareName): self
    {
        Validator::value($serverSoftwareName)
            ->valueIn(DatabaseEngine::AVAILABLE)
            ->validate();

        $this->serverSoftwareName = $serverSoftwareName;

        return $this;
    }

    public function getOptimizingEnabled(): ?bool
    {
        return $this->optimizingEnabled;
    }

    public function setOptimizingEnabled(?bool $optimizingEnabled): self
    {
        $this->optimizingEnabled = $optimizingEnabled;

        return $this;
    }

    public function getBackupsEnabled(): ?bool
    {
        return $this->backupsEnabled;
    }

    public function setBackupsEnabled(?bool $backupsEnabled): self
    {
        $this->backupsEnabled = $backupsEnabled;

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
            ->setServerSoftwareName(
                Arr::get(
                    $data,
                    'server_software_name',
                    DatabaseEngine::SERVER_SOFTWARE_MARIADB
                )
            )
            ->setBackupsEnabled(Arr::get($data, 'backups_enabled'))
            ->setOptimizingEnabled(Arr::get($data, 'optimizing_enabled'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'server_software_name' => $this->getServerSoftwareName(),
            'backups_enabled' => $this->getBackupsEnabled(),
            'optimizing_enabled' => $this->getOptimizingEnabled(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
