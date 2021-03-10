<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Command implements Model
{
    public string $command;
    public array $secretValues = [];
    public ?int $virtualHostId;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?int $returnCode = null;
    public ?string $standardOut = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Command
    {
        $command = new self();
        $command->command = Arr::get($data, 'command');
        $command->secretValues = Arr::get($data, 'secret_values', []);
        $command->virtualHostId = Arr::get($data, 'virtual_host_id');
        $command->id = Arr::get($data, 'id');
        $command->clusterId = Arr::get($data, 'cluster_id');
        $command->returnCode = Arr::get($data, 'return_code');
        $command->standardOut = Arr::get($data, 'standard_out');
        $command->createdAt = Arr::get($data, 'created_at');
        $command->updatedAt = Arr::get($data, 'updated_at');
        return $command;
    }

    public function toArray(): array
    {
        return [
            'command' => $this->command,
            'secret_values' => $this->secretValues,
            'virtual_host_id' => $this->virtualHostId,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'return_code' => $this->returnCode,
            'standard_out' => $this->standardOut,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
