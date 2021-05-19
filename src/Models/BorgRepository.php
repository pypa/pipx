<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class BorgRepository extends ClusterModel implements Model
{
    private string $name;
    private string $passphrase;
    private ?int $keepHourly = null;
    private ?int $keepDaily = null;
    private ?int $keepWeekly = null;
    private ?int $keepMonthly = null;
    private ?int $keepYearly = null;
    private ?string $remoteUrl = null;
    private int $sshKeyId;
    private int $unixUserId;
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
        $this->validate($name, [
            'length_max' => 64,
            'pattern' => '^[a-z0-9-_]+$',
        ]);

        $this->name = $name;

        return $this;
    }

    public function getPassphrase(): string
    {
        return $this->passphrase;
    }

    public function setPassphrase(string $passphrase): BorgRepository
    {
        $this->passphrase = $passphrase;

        return $this;
    }

    public function getKeepHourly(): ?int
    {
        return $this->keepHourly;
    }

    public function setKeepHourly(int $keepHourly = null): BorgRepository
    {
        $this->keepHourly = $keepHourly;

        return $this;
    }

    public function getKeepDaily(): ?int
    {
        return $this->keepDaily;
    }

    public function setKeepDaily(int $keepDaily = null): BorgRepository
    {
        $this->keepDaily = $keepDaily;

        return $this;
    }

    public function getKeepWeekly(): ?int
    {
        return $this->keepWeekly;
    }

    public function setKeepWeekly(int $keepWeekly = null): BorgRepository
    {
        $this->keepWeekly = $keepWeekly;

        return $this;
    }

    public function getKeepMonthly(): ?int
    {
        return $this->keepMonthly;
    }

    public function setKeepMonthly(int $keepMonthly = null): BorgRepository
    {
        $this->keepMonthly = $keepMonthly;

        return $this;
    }

    public function getKeepYearly(): ?int
    {
        return $this->keepYearly;
    }

    public function setKeepYearly(int $keepYearly = null): BorgRepository
    {
        $this->keepYearly = $keepYearly;

        return $this;
    }

    public function getRemoteUrl(): ?string
    {
        return $this->remoteUrl;
    }

    public function setRemoteUrl(?string $remoteUrl): BorgRepository
    {
        $this->remoteUrl = $remoteUrl;

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

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): BorgRepository
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
            ->setRemoteUrl(Arr::get($data, 'remote_url'))
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
            'remote_url' => $this->getRemoteUrl(),
            'ssh_key_id' => $this->getSshKeyId(),
            'unix_user_id' => $this->getUnixUserId(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
