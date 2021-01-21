<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Health implements Model
{
    public string $status;

    public function fromArray(array $data): Health
    {
        $health = new self();
        $health->status = Arr::get($data, 'status');
        return $health;
    }

    public function toArray(): array
    {
        return [
            'status' => $this->status,
        ];
    }
}
