<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Cron extends ClusterModel implements Model
{
    private string $name;
    private string $command;
    private string $emailAddress;
    private string $schedule;
    private int $unixUserId;
    private int $errorCount = 1;
    private bool $lockingEnabled = true;
    private bool $isActive = true;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): Cron
    {
        $this->validate($name, [
            'length_max' => 64,
            'pattern' => '^[a-z0-9-_.]+$',
        ]);

        $this->name = $name;

        return $this;
    }

    public function getCommand(): string
    {
        return $this->command;
    }

    public function setCommand(string $command): Cron
    {
        $this->command = $command;

        return $this;
    }

    public function getEmailAddress(): string
    {
        return $this->emailAddress;
    }

    public function setEmailAddress(string $emailAddress): Cron
    {
        $this->emailAddress = $emailAddress;

        return $this;
    }

    public function getSchedule(): string
    {
        return $this->schedule;
    }

    public function setSchedule(string $schedule): Cron
    {
        $this->schedule = $schedule;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): Cron
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getErrorCount(): int
    {
        return $this->errorCount;
    }

    public function setErrorCount(int $errorCount): Cron
    {
        $this->errorCount = $errorCount;

        return $this;
    }

    public function isLockingEnabled(): bool
    {
        return $this->lockingEnabled;
    }

    public function setLockingEnabled(bool $lockingEnabled): Cron
    {
        $this->lockingEnabled = $lockingEnabled;

        return $this;
    }

    public function isActive(): bool
    {
        return $this->isActive;
    }

    public function setIsActive(bool $isActive): Cron
    {
        $this->isActive = $isActive;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): Cron
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): Cron
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): Cron
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): Cron
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): Cron
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setCommand(Arr::get($data, 'command'))
            ->setEmailAddress(Arr::get($data, 'email_address'))
            ->setSchedule(Arr::get($data, 'schedule'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setErrorCount(Arr::get($data, 'error_count'))
            ->setLockingEnabled(Arr::get($data, 'locking_enabled'))
            ->setIsActive(Arr::get($data, 'is_active'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'command' => $this->getCommand(),
            'email_address' => $this->getEmailAddress(),
            'schedule' => $this->getSchedule(),
            'unix_user_id' => $this->getUnixUserId(),
            'error_count' => $this->getErrorCount(),
            'locking_enabled' => $this->isLockingEnabled(),
            'is_active' => $this->isActive(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
