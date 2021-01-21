<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class MailDomain implements Model
{
    public string $domain;
    public int $unixUserId;
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): MailDomain
    {
        $mailDomain = new self();
        $mailDomain->domain = Arr::get($data, 'domain');
        $mailDomain->unixUserId = Arr::get($data, 'unix_user_id');
        $mailDomain->id = Arr::get($data, 'id');
        $mailDomain->clusterId = Arr::get($data, 'cluster_id');
        $mailDomain->createdAt = Arr::get($data, 'created_at');
        $mailDomain->updatedAt = Arr::get($data, 'updated_at');
        return $mailDomain;
    }

    public function toArray(): array
    {
        return [
            'domain' => $this->domain,
            'unix_user_id' => $this->unixUserId,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
