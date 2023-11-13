<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\TaskCollectionType;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class TaskCollection extends ClusterModel
{
    private string $uuid;
    private string $description;
    private string $collectionType;
    private ?string $objectId = null;
    private string $objectModelName;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getUuid(): string
    {
        return $this->uuid;
    }

    public function setUuid(string $uuid): self
    {
        $this->uuid = $uuid;

        return $this;
    }

    public function getDescription(): string
    {
        return $this->description;
    }

    public function setDescription(string $description): self
    {
        Validator::value($description)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->description = $description;

        return $this;
    }

    public function getCollectionType(): string
    {
        return $this->collectionType;
    }

    public function setCollectionType(string $collectionType): self
    {
        Validator::value($collectionType)
            ->valueIn(TaskCollectionType::AVAILABLE)
            ->validate();

        $this->collectionType = $collectionType;

        return $this;
    }

    public function getObjectId(): ?string
    {
        return $this->objectId;
    }

    public function setObjectId(?string $objectId): self
    {
        $this->objectId = $objectId;

        return $this;
    }

    public function getObjectModelName(): string
    {
        return $this->objectModelName;
    }

    public function setObjectModelName(string $objectModelName): self
    {
        $this->objectModelName = $objectModelName;

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
            ->setUuid(Arr::get($data, 'uuid'))
            ->setDescription(Arr::get($data, 'description'))
            ->setCollectionType(Arr::get($data, 'collection_type'))
            ->setObjectId(Arr::get($data, 'object_id'))
            ->setObjectModelName(Arr::get($data, 'object_model_name'))
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
            'object_id' => $this->getObjectId(),
            'object_model_name' => $this->getObjectModelName(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
