<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class MailAccount extends ClusterModel implements Model
{
    private string $localPart;
    private string $password;
    private ?int $quota = null;
    private int $mailDomainId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getLocalPart(): string
    {
        return $this->localPart;
    }

    public function setLocalPart(string $localPart): MailAccount
    {
        $this->validate($localPart, [
            'length_max' => 64,
        ]);

        $this->localPart = $localPart;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): MailAccount
    {
        $this->password = $password;

        return $this;
    }

    public function getQuota(): ?int
    {
        return $this->quota;
    }

    public function setQuota(?int $quota): MailAccount
    {
        $this->quota = $quota;

        return $this;
    }

    public function getMailDomainId(): int
    {
        return $this->mailDomainId;
    }

    public function setMailDomainId(int $mailDomainId): MailAccount
    {
        $this->mailDomainId = $mailDomainId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): MailAccount
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): MailAccount
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): MailAccount
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): MailAccount
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): MailAccount
    {
        return $this
            ->setLocalPart(Arr::get($data, 'local_part'))
            ->setPassword(Arr::get($data, 'password'))
            ->setQuota(Arr::get($data, 'quota'))
            ->setMailDomainId(Arr::get($data, 'mail_domain_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'local_part' => $this->getLocalPart(),
            'password' => $this->getPassword(),
            'quota' => $this->getQuota(),
            'mail_domain_id' => $this->getMailDomainId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
