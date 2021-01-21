<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class UnixUserUsage implements Model
{
    public int $unixUserId;
    public int $usage;
    public array $files = [];
    public string $timestamp;

    public function fromArray(array $data): UnixUserUsage
    {
        $unixUserUsage = new self();
        $unixUserUsage->unixUserId = Arr::get($data, 'unix_user_id');
        $unixUserUsage->usage = Arr::get($data, 'usage');
        $unixUserUsage->files = Arr::get($data, 'files');
        $unixUserUsage->timestamp = Arr::get($data, 'timestamp');
        return $unixUserUsage;
    }

    public function toArray(): array
    {
        return [
            'unix_user_id' => $this->unixUserId,
            'usage' => $this->usage,
            'files' => $this->files,
            'timestamp' => $this->timestamp,
        ];
    }
}
