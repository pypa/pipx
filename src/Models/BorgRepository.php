<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Support\Validator;

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

    public function setName(string $name): BorgRepository
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

    public function setPassphrase(string $passphrase): BorgRepository
    {
        Validator::value($passphrase)
            ->maxLength(255)
            ->minLength(1)
            ->validate();

        $this->passphrase = $passphrase;

        return $this;
    }

    public function getKeepHourly(): ?int
    {
        return $this->keepHourly;
    }

    public function setKeepHourly(int $keepHourly = null): BorgRepository
    {
        Validator::value($keepHourly)
            ->nullable()
            ->positiveInteger()
            ->validate();

        $this->keepHourly = $keepHourly;

        return $this;
    }

    public function getKeepDaily(): ?int
    {
        return $this->keepDaily;
    }

    public function setKeepDaily(int $keepDaily = null): BorgRepository
    {
        Validator::value($keepDaily)
            ->nullable()
            ->positiveInteger()
            ->validate();

        $this->keepDaily = $keepDaily;

        return $this;
    }

    public function getKeepWeekly(): ?int
    {
        return $this->keepWeekly;
    }

    public function setKeepWeekly(int $keepWeekly = null): BorgRepository
    {
        Validator::value($keepWeekly)
            ->nullable()
            ->positiveInteger()
            ->validate();

        $this->keepWeekly = $keepWeekly;

        return $this;
    }

    public function getKeepMonthly(): ?int
    {
        return $this->keepMonthly;
    }

    public function setKeepMonthly(int $keepMonthly = null): BorgRepository
    {
        Validator::value($keepMonthly)
            ->nullable()
            ->positiveInteger()
            ->validate();

        $this->keepMonthly = $keepMonthly;

        return $this;
    }

    public function getKeepYearly(): ?int
    {
        return $this->keepYearly;
    }

    public function setKeepYearly(int $keepYearly = null): BorgRepository
    {
        Validator::value($keepYearly)
            ->nullable()
            ->positiveInteger()
            ->validate();

        $this->keepYearly = $keepYearly;

        return $this;
    }

    public function getRemoteHost(): ?string
    {
        return $this->remoteHost;
    }

    public function setRemoteHost(?string $remoteHost): BorgRepository
    {
        $this->remoteHost = $remoteHost;

        return $this;
    }

    public function getRemotePath(): ?string
    {
        return $this->remotePath;
    }

    public function setRemotePath(?string $remotePath): BorgRepository
    {
        $this->remotePath = $remotePath;

        return $this;
    }

    public function getRemoteUsername(): ?string
    {
        return $this->remoteUsername;
    }

    public function setRemoteUsername(?string $remoteUsername): BorgRepository
    {
        $this->remoteUsername = $remoteUsername;

        return $this;
    }

    public function getIdentityFilePath(): ?string
    {
        return $this->identityFilePath;
    }

    public function setIdentityFilePath(?string $identityFilePath): BorgRepository
    {
        $this->identityFilePath = $identityFilePath;

        return $this;
    }

    public function getSshKeyId(): int
    {
        return $this->sshKeyId;
    }

    public function setSshKeyId(int $sshKeyId): BorgRepository
    {
        $this->sshKeyId = $sshKeyId;

        return $this;
    }

    public function getUnixUserId(): ?int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(?int $unixUserId): BorgRepository
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): BorgRepository
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): BorgRepository
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): BorgRepository
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): BorgRepository
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): BorgRepository
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
            ->setSshKeyId(Arr::get($data, 'ssh_key_id'))
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
            'ssh_key_id' => $this->getSshKeyId(),
            'unix_user_id' => $this->getUnixUserId(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
