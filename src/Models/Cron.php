<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Cron implements Model
{
    public string $name;
    public string $command;
    public string $emailAddress;
    public string $schedule;
    public int $unixUserId;
    public int $errorCount = 1;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Cron
    {
        $cron = new self();
        $cron->name = Arr::get($data, 'name');
        $cron->command = Arr::get($data, 'command');
        $cron->emailAddress = Arr::get($data, 'email_address');
        $cron->schedule = Arr::get($data, 'schedule');
        $cron->unixUserId = Arr::get($data, 'unix_user_id');
        $cron->errorCount = Arr::get($data, 'error_count');
        $cron->id = Arr::get($data, 'id');
        $cron->clusterId = Arr::get($data, 'cluster_id');
        $cron->createdAt = Arr::get($data, 'created_at');
        $cron->updatedAt = Arr::get($data, 'updated_at');
        return $cron;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'command' => $this->command,
            'email_address' => $this->emailAddress,
            'schedule' => $this->schedule,
            'unix_user_id' => $this->unixUserId,
            'error_count' => $this->errorCount,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
