<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Enums\DatabaseEngine;

class Database extends ClusterModel implements Model
{
    private string $name;
    private string $serverSoftwareName = DatabaseEngine::SERVER_SOFTWARE_MARIADB;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): Database
    {
        $this->validate($name, [
            'length_max' => 63,
            'pattern' => '^[a-zA-Z0-9-_]+$',
        ]);

        $this->name = $name;

        return $this;
    }

    public function getServerSoftwareName(): string
    {
        return $this->serverSoftwareName;
    }

    public function setServerSoftwareName(string $serverSoftwareName): Database
    {
        $this->validate($serverSoftwareName, [
            'in' => DatabaseEngine::AVAILABLE_SERVER_SOFTWARE,
        ]);

        $this->serverSoftwareName = $serverSoftwareName;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): Database
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): Database
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): Database
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): Database
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): Database
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setServerSoftwareName(Arr::get(
                $data,
                'server_software_name',
                DatabaseEngine::SERVER_SOFTWARE_MARIADB
            ))
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
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
