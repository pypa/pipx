<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class MailAlias implements Model
{
    public string $localPart;
    public array $forwardEmailAddresses = [];
    public ?int $mailDomainId = null;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): MailAlias
    {
        $mailAlias = new self();
        $mailAlias->localPart = Arr::get($data, 'local_part');
        $mailAlias->forwardEmailAddresses = Arr::get($data, 'forward_email_addresses', []);
        $mailAlias->mailDomainId = Arr::get($data, 'mail_domain_id');
        $mailAlias->id = Arr::get($data, 'id');
        $mailAlias->clusterId = Arr::get($data, 'cluster_id');
        $mailAlias->createdAt = Arr::get($data, 'created_at');
        $mailAlias->updatedAt = Arr::get($data, 'updated_at');
        return $mailAlias;
    }

    public function toArray(): array
    {
        return [
            'local_part' => $this->localPart,
            'forward_email_addresses' => $this->forwardEmailAddresses,
            'mail_domain_id' => $this->mailDomainId,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
