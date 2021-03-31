<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class UnixUserUsage extends ClusterModel implements Model
{
    private int $unixUserId;
    private int $usage;
    private array $files = [];
    private string $timestamp;

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): UnixUserUsage
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getUsage(): int
    {
        return $this->usage;
    }

    public function setUsage(int $usage): UnixUserUsage
    {
        $this->usage = $usage;

        return $this;
    }

    public function getFiles(): array
    {
        return $this->files;
    }

    public function setFiles(array $files): UnixUserUsage
    {
        $this->files = $files;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): UnixUserUsage
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function fromArray(array $data): UnixUserUsage
    {
        return $this
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setUsage(Arr::get($data, 'usage'))
            ->setFiles(Arr::get($data, 'files'))
            ->setTimestamp(Arr::get($data, 'timestamp'));
    }

    public function toArray(): array
    {
        return [
            'unix_user_id' => $this->getUnixUserId(),
            'usage' => $this->getUsage(),
            'files' => $this->getFiles(),
            'timestamp' => $this->getTimestamp(),
        ];
    }
}
