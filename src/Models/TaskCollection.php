<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Enums\TaskCollectionType;
use Vdhicts\Cyberfusion\ClusterApi\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Support\Validator;

class TaskCollection extends ClusterModel implements Model
{
    private string $uuid;
    private string $description;
    private string $collectionType;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getUuid(): string
    {
        return $this->uuid;
    }

    public function setUuid(string $uuid): TaskCollection
    {
        $this->uuid = $uuid;

        return $this;
    }

    public function getDescription(): string
    {
        return $this->description;
    }

    public function setDescription(string $description): TaskCollection
    {
        Validator::value($description)
            ->minLength(1)
            ->maxLength(255)
            ->validate();

        $this->description = $description;

        return $this;
    }

    public function getCollectionType(): string
    {
        return $this->collectionType;
    }

    public function setCollectionType(string $collectionType): TaskCollection
    {
        Validator::value($collectionType)
            ->valueIn(TaskCollectionType::AVAILABLE)
            ->validate();

        $this->collectionType = $collectionType;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): TaskCollection
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): TaskCollection
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): TaskCollection
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): TaskCollection
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): TaskCollection
    {
        return $this
            ->setUuid(Arr::get($data, 'uuid'))
            ->setDescription(Arr::get($data, 'description'))
            ->setCollectionType(Arr::get($data, 'collection_type'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'uuid' => $this->getUuid(),
            'description' => $this->getDescription(),
            'collection_type' => $this->getCollectionType(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
