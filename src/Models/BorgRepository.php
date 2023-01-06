<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class BorgRepository extends ClusterModel implements Model
{
    private string $name;
    private string $passphrase;
    private ?int $keepHourly = null;
    private ?int $keepDaily = null;
    private ?int $keepWeekly = null;
    private ?int $keepMonthly = null;
    private ?int $keepYearly = null;
    private ?string $remoteHost = null;
    private ?string $remotePath = null;
    private ?string $remoteUsername = null;
    private ?string $identityFilePath = null;
    private ?int $unixUserId = null;
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
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getPassphrase(): string
    {
        return $this->passphrase;
    }

    public function setPassphrase(string $passphrase): self
    {
        Validator::value($passphrase)
            ->minLength(24)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->passphrase = $passphrase;

        return $this;
    }

    public function getKeepHourly(): ?int
    {
        return $this->keepHourly;
    }

    public function setKeepHourly(int $keepHourly = null): self
    {
        $this->keepHourly = $keepHourly;

        return $this;
    }

    public function getKeepDaily(): ?int
    {
        return $this->keepDaily;
    }

    public function setKeepDaily(int $keepDaily = null): self
    {
        $this->keepDaily = $keepDaily;

        return $this;
    }

    public function getKeepWeekly(): ?int
    {
        return $this->keepWeekly;
    }

    public function setKeepWeekly(int $keepWeekly = null): self
    {
        $this->keepWeekly = $keepWeekly;

        return $this;
    }

    public function getKeepMonthly(): ?int
    {
        return $this->keepMonthly;
    }

    public function setKeepMonthly(int $keepMonthly = null): self
    {
        $this->keepMonthly = $keepMonthly;

        return $this;
    }

    public function getKeepYearly(): ?int
    {
        return $this->keepYearly;
    }

    public function setKeepYearly(int $keepYearly = null): self
    {
        $this->keepYearly = $keepYearly;

        return $this;
    }

    public function getRemoteHost(): ?string
    {
        return $this->remoteHost;
    }

    public function setRemoteHost(?string $remoteHost): self
    {
        $this->remoteHost = $remoteHost;

        return $this;
    }

    public function getRemotePath(): ?string
    {
        return $this->remotePath;
    }

    public function setRemotePath(?string $remotePath): self
    {
        Validator::value($remotePath)
            ->nullable()
            ->path()
            ->validate();

        $this->remotePath = $remotePath;

        return $this;
    }

    public function getRemoteUsername(): ?string
    {
        return $this->remoteUsername;
    }

    public function setRemoteUsername(?string $remoteUsername): self
    {
        Validator::value($remoteUsername)
            ->nullable()
            ->maxLength(32)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->remoteUsername = $remoteUsername;

        return $this;
    }

    public function getIdentityFilePath(): ?string
    {
        return $this->identityFilePath;
    }

    public function setIdentityFilePath(?string $identityFilePath): self
    {
        Validator::value($identityFilePath)
            ->nullable()
            ->path()
            ->validate();

        $this->identityFilePath = $identityFilePath;

        return $this;
    }

    public function getUnixUserId(): ?int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(?int $unixUserId): self
    {
        $this->unixUserId = $unixUserId;

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
            ->setPassphrase(Arr::get($data, 'passphrase'))
            ->setKeepHourly(Arr::get($data, 'keep_hourly'))
            ->setKeepDaily(Arr::get($data, 'keep_daily'))
            ->setKeepWeekly(Arr::get($data, 'keep_weekly'))
            ->setKeepMonthly(Arr::get($data, 'keep_monthly'))
            ->setRemoteHost(Arr::get($data, 'remote_host'))
            ->setRemotePath(Arr::get($data, 'remote_path'))
            ->setRemoteUsername(Arr::get($data, 'remote_username'))
            ->setIdentityFilePath(Arr::get($data, 'identity_file_path'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setId(Arr::get($data, 'id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'passphrase' => $this->getPassphrase(),
            'keep_hourly' => $this->getKeepHourly(),
            'keep_daily' => $this->getKeepDaily(),
            'keep_weekly' => $this->getKeepWeekly(),
            'keep_monthly' => $this->getKeepMonthly(),
            'keep_yearly' => $this->getKeepYearly(),
            'remote_host' => $this->getRemoteHost(),
            'remote_path' => $this->getRemotePath(),
            'remote_username' => $this->getRemoteUsername(),
            'identity_file_path' => $this->getIdentityFilePath(),
            'unix_user_id' => $this->getUnixUserId(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
