<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;

class MailAccountUsage extends ClusterModel implements Model
{
    private int $mailAccountId;
    private int $usage;
    private string $timestamp;

    public function getMailAccountId(): int
    {
        return $this->mailAccountId;
    }

    public function setMailAccountId(int $mailAccountId): self
    {
        $this->mailAccountId = $mailAccountId;

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
            ->setMailAccountId(Arr::get($data, 'mail_account_id'))
            ->setUsage(Arr::get($data, 'usage'))
            ->setTimestamp(Arr::get($data, 'timestamp'));
    }

    public function toArray(): array
    {
        return [
            'mail_account_id' => $this->getMailAccountId(),
            'usage' => $this->getUsage(),
            'timestamp' => $this->getTimestamp(),
        ];
    }
}
