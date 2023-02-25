<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\HealthStatus;
use Cyberfusion\ClusterApi\Support\Arr;

class Health extends ClusterModel
{
    private string $status;

    public function getStatus(): string
    {
        return $this->status;
    }

    public function setStatus(string $status): self
    {
        $this->status = $status;

        return $this;
    }

    public function fromArray(array $data): self
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
