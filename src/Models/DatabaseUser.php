<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\DatabaseEngine;
use Cyberfusion\ClusterApi\Enums\Host;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class DatabaseUser extends ClusterModel
{
    private const DEFAULT_HOST = '%';

    private string $name;
    private ?string $password;
    private ?array $phpmyadminFirewallGroupsIds = null;
    private string $host = self::DEFAULT_HOST;
    private string $serverSoftwareName = DatabaseEngine::SERVER_SOFTWARE_MARIADB;
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
            ->maxLength(63)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getHost(): string
    {
        return $this->host;
    }

    public function setHost(string $host): self
    {
        Validator::value($host)
            ->maxLength(253)
            ->valueIn(Host::AVAILABLE)
            ->validate();

        $this->host = $host;

        return $this;
    }

    public function getPassword(): ?string
    {
        return $this->password;
    }

    public function setPassword(?string $password): self
    {
        Validator::value($password)
            ->nullable()
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->password = $password;

        return $this;
    }

    public function getPhpmyadminFirewallGroupsIds(): ?array
    {
        return $this->phpmyadminFirewallGroupsIds;
    }

    public function setPhpmyadminFirewallGroupsIds(?array $phpmyadminFirewallGroupsIds): self
    {
        $this->phpmyadminFirewallGroupsIds = $phpmyadminFirewallGroupsIds;

        return $this;
    }

    public function getServerSoftwareName(): string
    {
        return $this->serverSoftwareName;
    }

    public function setServerSoftwareName(string $serverSoftwareName): self
    {
        Validator::value($serverSoftwareName)
            ->valueIn(DatabaseEngine::AVAILABLE)
            ->validate();

        $this->serverSoftwareName = $serverSoftwareName;

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
            ->setPassword(Arr::get($data, 'password'))
            ->setPhpmyadminFirewallGroupsIds(Arr::get($data, 'phpmyadmin_firewall_groups_ids'))
            ->setId(Arr::get($data, 'id'))
            ->setHost(Arr::get($data, 'host', self::DEFAULT_HOST))
            ->setServerSoftwareName(
                Arr::get(
                    $data,
                    'server_software_name',
                    DatabaseEngine::SERVER_SOFTWARE_MARIADB
                )
            )
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
            'phpmyadmin_firewall_groups_ids' => $this->getPhpmyadminFirewallGroupsIds(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
