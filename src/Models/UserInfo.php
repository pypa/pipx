<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;

class UserInfo extends ClusterModel implements Model
{
    private int $id;
    private string $username;
    private bool $isActive;
    private bool $isProvisioningUser;
    private bool $isSuperUser;
    private array $clusters = [];

    public function getId(): int
    {
        return $this->id;
    }

    public function setId(int $id): UserInfo
    {
        $this->id = $id;

        return $this;
    }

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): UserInfo
    {
        $this->username = $username;

        return $this;
    }

    public function isActive(): bool
    {
        return $this->isActive;
    }

    public function setIsActive(bool $isActive): UserInfo
    {
        $this->isActive = $isActive;

        return $this;
    }

    public function isProvisioningUser(): bool
    {
        return $this->isProvisioningUser;
    }

    public function setIsProvisioningUser(bool $isProvisioningUser): UserInfo
    {
        $this->isProvisioningUser = $isProvisioningUser;

        return $this;
    }

    public function isSuperUser(): bool
    {
        return $this->isSuperUser;
    }

    public function setIsSuperUser(bool $isSuperUser): UserInfo
    {
        $this->isSuperUser = $isSuperUser;

        return $this;
    }

    public function getClusters(): array
    {
        return $this->clusters;
    }

    public function setClusters(array $clusters): UserInfo
    {
        $this->clusters = $clusters;

        return $this;
    }

    public function fromArray(array $data): UserInfo
    {
        return $this
            ->setId(Arr::get($data, 'id'))
            ->setUsername(Arr::get($data, 'username'))
            ->setIsActive(Arr::get($data, 'is_active'))
            ->setIsProvisioningUser(Arr::get($data, 'is_provisioning_user'))
            ->setIsSuperUser(Arr::get($data, 'is_superuser'))
            ->setClusters(Arr::get($data, 'clusters', []));
    }

    public function toArray(): array
    {
        return [
            'id' => $this->getId(),
            'username' => $this->getUsername(),
            'is_active' => $this->isActive(),
            'is_provisioning_user' => $this->isProvisioningUser(),
            'is_superuser' => $this->isSuperUser(),
            'clusters' => $this->getClusters(),
        ];
    }
}
