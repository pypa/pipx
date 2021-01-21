<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class MailAccount implements Model
{
    public string $localPart;
    public string $password;
    public array $forwardEmailAddresses = [];
    public ?int $quota = null;
    public int $mailDomainId;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): MailAccount
    {
        $mailAccount = new self();
        $mailAccount->localPart = Arr::get($data, 'local_part');
        $mailAccount->password = Arr::get($data, 'password');
        $mailAccount->forwardEmailAddresses = Arr::get($data, 'forward_email_addresses', []);
        $mailAccount->quota = Arr::get($data, 'quota');
        $mailAccount->mailDomainId = Arr::get($data, 'mail_domain_id');
        $mailAccount->id = Arr::get($data, 'id');
        $mailAccount->clusterId = Arr::get($data, 'cluster_id');
        $mailAccount->createdAt = Arr::get($data, 'created_at');
        $mailAccount->updatedAt = Arr::get($data, 'updated_at');
        return $mailAccount;
    }

    public function toArray(): array
    {
        return [
            'local_part' => $this->localPart,
            'password' => $this->password,
            'forward_email_addresses' => $this->forwardEmailAddresses,
            'quota' => $this->quota,
            'mail_domain_id' => $this->mailDomainId,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
