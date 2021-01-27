<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Enums\HealthStatus;

class Health implements Model
{
    public string $status;

    public function fromArray(array $data): Health
    {
        $health = new self();
        $health->status = Arr::get($data, 'status');
        return $health;
    }

    public function isUp(): bool
    {
        return $this->status === HealthStatus::UP;
    }

    public function toArray(): array
    {
        return [
            'status' => $this->status,
        ];
    }
}
