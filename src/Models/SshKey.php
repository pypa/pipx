<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class SshKey extends ClusterModel implements Model
{
    private string $name;
    private string $publicKey;
    private ?string $privateKey = null;
    private int $unixUserId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): SshKey
    {
        $this->validate($name, [
            'length_max' => 64,
            'pattern' => '^[a-zA-Z0-9-_@:. ]+$',
        ]);

        $this->name = $name;

        return $this;
    }

    public function getPublicKey(): string
    {
        return $this->publicKey;
    }

    public function setPublicKey(string $publicKey): SshKey
    {
        $this->publicKey = $publicKey;

        return $this;
    }

    public function getPrivateKey(): ?string
    {
        return $this->privateKey;
    }

    public function setPrivateKey(?string $privateKey): SshKey
    {
        $this->privateKey = $privateKey;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): SshKey
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): SshKey
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): SshKey
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): SshKey
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): SshKey
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): SshKey
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setPublicKey(Arr::get($data, 'public_key'))
            ->setPrivateKey(Arr::get($data, 'private_key'))
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
            'public_key' => $this->getPublicKey(),
            'private_key' => $this->getPrivateKey(),
            'unix_user_id' => $this->getUnixUserId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
