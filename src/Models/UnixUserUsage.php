<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class UnixUserUsage extends ClusterModel implements Model
{
    private int $unixUserId;
    private int $usage;
    private ?array $files = null;
    private string $timestamp;

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): self
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getUsage(): int
    {
        return $this->usage;
    }

    public function setUsage(int $usage): self
    {
        $this->usage = $usage;

        return $this;
    }

    public function getFiles(): ?array
    {
        return $this->files;
    }

    public function setFiles(?array $files): self
    {
        Validator::value($files)
            ->nullable()
            ->each()
            ->path()
            ->validate();

        $this->files = $files;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): self
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function fromArray(array $data): self
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
