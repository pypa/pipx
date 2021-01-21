<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class MailAccountUsage implements Model
{
    public int $mailAccountId;
    public int $usage;
    public string $timestamp;

    public function fromArray(array $data): MailAccountUsage
    {
        $mailAccountUsage = new self();
        $mailAccountUsage->mailAccountId = Arr::get($data, 'mail_account_id');
        $mailAccountUsage->usage = Arr::get($data, 'usage');
        $mailAccountUsage->timestamp = Arr::get($data, 'timestamp');
        return $mailAccountUsage;
    }

    public function toArray(): array
    {
        return [
            'mail_account_id' => $this->mailAccountId,
            'usage' => $this->usage,
            'timestamp' => $this->timestamp,
        ];
    }
}
