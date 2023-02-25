<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;

class Cms extends ClusterModel
{
    private string $softwareName;
    private int $virtualHostId;
    private bool $isManuallyCreated = false;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getSoftwareName(): string
    {
        return $this->softwareName;
    }

    public function setSoftwareName(string $softwareName): self
    {
        $this->softwareName = $softwareName;

        return $this;
    }

    public function getVirtualHostId(): int
    {
        return $this->virtualHostId;
    }

    public function setVirtualHostId(int $virtualHostId): self
    {
        $this->virtualHostId = $virtualHostId;

        return $this;
    }

    public function isManuallyCreated(): bool
    {
        return $this->isManuallyCreated;
    }

    public function setIsManuallyCreated(bool $isManuallyCreated): self
    {
        $this->isManuallyCreated = $isManuallyCreated;

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
            ->setSoftwareName(Arr::get($data, 'software_name'))
            ->setVirtualHostId(Arr::get($data, 'virtual_host_id'))
            ->setIsManuallyCreated(Arr::get($data, 'is_manually_created'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'software_name' => $this->getSoftwareName(),
            'virtual_host_id' => $this->getVirtualHostId(),
            'is_manually_created' => $this->isManuallyCreated(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
