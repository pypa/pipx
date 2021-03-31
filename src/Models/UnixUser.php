<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class UnixUser extends ClusterModel implements Model
{
    private string $username;
    private string $password;
    private ?string $defaultPhpVersion = null;
    private ?string $virtualHostsDirectory = null;
    private ?string $mailDomainsDirectory = null;
    private int $clusterId;
    private ?int $id = null;
    private ?int $unixId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): UnixUser
    {
        $this->validate($username, [
            'length_max' => 32,
            'pattern' => '^[a-z0-9-_]+$',
        ]);

        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): UnixUser
    {
        $this->password = $password;

        return $this;
    }

    public function getDefaultPhpVersion(): ?string
    {
        return $this->defaultPhpVersion;
    }

    public function setDefaultPhpVersion(?string $defaultPhpVersion): UnixUser
    {
        $this->defaultPhpVersion = $defaultPhpVersion;

        return $this;
    }

    public function getVirtualHostsDirectory(): ?string
    {
        return $this->virtualHostsDirectory;
    }

    public function setVirtualHostsDirectory(?string $virtualHostsDirectory): UnixUser
    {
        $this->virtualHostsDirectory = $virtualHostsDirectory;

        return $this;
    }

    public function getMailDomainsDirectory(): ?string
    {
        return $this->mailDomainsDirectory;
    }

    public function setMailDomainsDirectory(?string $mailDomainsDirectory): UnixUser
    {
        $this->mailDomainsDirectory = $mailDomainsDirectory;

        return $this;
    }

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): UnixUser
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): UnixUser
    {
        $this->id = $id;

        return $this;
    }

    public function getUnixId(): ?int
    {
        return $this->unixId;
    }

    public function setUnixId(?int $unixId): UnixUser
    {
        $this->unixId = $unixId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): UnixUser
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): UnixUser
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): UnixUser
    {
        return $this
            ->setUsername(Arr::get($data, 'username'))
            ->setPassword(Arr::get($data, 'password'))
            ->setDefaultPhpVersion(Arr::get($data, 'default_php_version'))
            ->setVirtualHostsDirectory(Arr::get($data, 'virtual_hosts_directory'))
            ->setMailDomainsDirectory(Arr::get($data, 'mail_domains_directory'))
            ->setUnixId(Arr::get($data, 'unix_id'))
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
            'default_php_version' => $this->getDefaultPhpVersion(),
            'virtual_hosts_directory' => $this->getVirtualHostsDirectory(),
            'mail_domains_directory' => $this->getMailDomainsDirectory(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'unix_id' => $this->getUnixId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
