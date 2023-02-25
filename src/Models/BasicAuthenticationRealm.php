<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class BasicAuthenticationRealm extends ClusterModel
{
    private string $name;
    private string $directoryPath;
    private int $virtualHostId;
    private int $htpasswdFileId;
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
            ->pattern('^[a-zA-Z0-9-_ ]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getDirectoryPath(): string
    {
        return $this->directoryPath;
    }

    public function setDirectoryPath(string $directoryPath): self
    {
        Validator::value($directoryPath)
            ->path()
            ->validate();

        $this->directoryPath = $directoryPath;

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

    public function getHtpasswdFileId(): int
    {
        return $this->htpasswdFileId;
    }

    public function setHtpasswdFileId(int $htpasswdFileId): self
    {
        $this->htpasswdFileId = $htpasswdFileId;

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
            ->setDirectoryPath(Arr::get($data, 'directory_path'))
            ->setVirtualHostId(Arr::get($data, 'virtual_host_id'))
            ->setHtpasswdFileId(Arr::get($data, 'htpasswd_file_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'directory_path' => $this->getDirectoryPath(),
            'virtual_host_id' => $this->getVirtualHostId(),
            'htpasswd_file_id' => $this->getHtpasswdFileId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
