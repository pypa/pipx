<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Enums\DatabaseEngine;

class DatabaseUser extends ClusterModel implements Model
{
    private const DEFAULT_HOST = '%';

    private string $name;
    private string $host = self::DEFAULT_HOST;
    private string $password = '';
    private string $serverSoftwareName = DatabaseEngine::SERVER_SOFTWARE_MARIADB;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): DatabaseUser
    {
        $this->validate($name, [
            'length_max' => 63,
            'pattern' => '^[a-zA-Z0-9-_]+$',
        ]);

        $this->name = $name;

        return $this;
    }

    public function getHost(): string
    {
        return $this->host;
    }

    public function setHost(string $host): DatabaseUser
    {
        $this->validate($host, [
            'length_max' => 253,
        ]);

        $this->host = $host;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): DatabaseUser
    {
        $this->password = $password;

        return $this;
    }

    public function getServerSoftwareName(): string
    {
        return $this->serverSoftwareName;
    }

    public function setServerSoftwareName(string $serverSoftwareName): DatabaseUser
    {
        $this->validate($serverSoftwareName, [
            'in' => DatabaseEngine::AVAILABLE,
        ]);

        $this->serverSoftwareName = $serverSoftwareName;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): DatabaseUser
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): DatabaseUser
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): DatabaseUser
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): DatabaseUser
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): DatabaseUser
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setId(Arr::get($data, 'id'))
            ->setHost(Arr::get($data, 'host', self::DEFAULT_HOST))
            ->setServerSoftwareName(Arr::get(
                $data,
                'server_software_name',
                DatabaseEngine::SERVER_SOFTWARE_MARIADB
            ))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'host' => $this->getHost(),
            'password' => $this->getPassword(),
            'server_software_name' => $this->getServerSoftwareName(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
