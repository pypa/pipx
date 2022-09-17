<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;

class HtpasswdUser extends ClusterModel implements Model
{
    private string $username;
    private string $password;
    private int $htpasswdFileId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): HtpasswdUser
    {
        Validator::value($username)
            ->maxLength(255)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): HtpasswdUser
    {
        $this->password = $password;

        return $this;
    }

    public function getHtpasswdFileId(): int
    {
        return $this->htpasswdFileId;
    }

    public function setHtpasswdFileId(int $htpasswdFileId): HtpasswdUser
    {
        $this->htpasswdFileId = $htpasswdFileId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): HtpasswdUser
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): HtpasswdUser
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): HtpasswdUser
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): HtpasswdUser
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): HtpasswdUser
    {
        return $this
            ->setUsername(Arr::get($data, 'username'))
            ->setPassword(Arr::get($data, 'password'))
            ->setHtpasswdFileId(Arr::get($data, 'htpasswd_file_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'username' => $this->getUsername(),
            'password' => $this->getPassword(),
            'htpasswd_file_id' => $this->getHtpasswdFileId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
