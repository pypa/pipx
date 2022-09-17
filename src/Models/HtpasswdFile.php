<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;

class HtpasswdFile extends ClusterModel implements Model
{
    private int $unixUserId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): HtpasswdFile
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): HtpasswdFile
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): HtpasswdFile
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): HtpasswdFile
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): HtpasswdFile
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): HtpasswdFile
    {
        return $this
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'unix_user_id' => $this->getUnixUserId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
