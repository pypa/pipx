<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class BorgArchive extends ClusterModel implements Model
{
    private string $name;
    private ?int $borgRepositoryId = null;
    private ?int $databaseId = null;
    private ?int $unixUserId = null;
    private ?int $id = null;
    private int $clusterId;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): BorgArchive
    {
        $this->name = $name;

        return $this;
    }

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): BorgArchive
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getBorgRepositoryId(): ?int
    {
        return $this->borgRepositoryId;
    }

    public function setBorgRepositoryId(?int $borgRepositoryId): BorgArchive
    {
        $this->borgRepositoryId = $borgRepositoryId;

        return $this;
    }

    public function getDatabaseId(): ?int
    {
        return $this->databaseId;
    }

    public function setDatabaseId(?int $databaseId): BorgArchive
    {
        $this->databaseId = $databaseId;

        return $this;
    }

    public function getUnixUserId(): ?int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(?int $unixUserId): BorgArchive
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): BorgArchive
    {
        $this->id = $id;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): BorgArchive
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): BorgArchive
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): BorgArchive
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setBorgRepositoryId(Arr::get($data, 'borg_repository_id'))
            ->setDatabaseId(Arr::get($data, 'database_id'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'borg_repository_id' => $this->getBorgRepositoryId(),
            'database_id' => $this->getDatabaseId(),
            'unix_user_id' => $this->getUnixUserId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
