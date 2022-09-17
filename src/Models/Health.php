<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Enums\HealthStatus;

class Health extends ClusterModel implements Model
{
    private string $status;

    public function getStatus(): string
    {
        return $this->status;
    }

    public function setStatus(string $status): Health
    {
        $this->status = $status;

        return $this;
    }

    public function fromArray(array $data): Health
    {
        return $this->setStatus(Arr::get($data, 'status'));
    }

    public function toArray(): array
    {
        return [
            'status' => $this->getStatus(),
        ];
    }

    public function isUp(): bool
    {
        return $this->getStatus() === HealthStatus::UP;
    }
}
