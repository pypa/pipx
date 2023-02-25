<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class MailAccount extends ClusterModel
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

    public function setLocalPart(string $localPart): self
    {
        Validator::value($localPart)
            ->pattern('^[a-z0-9-.]+$')
            ->maxLength(64)
            ->validate();

        $this->localPart = $localPart;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): self
    {
        Validator::value($password)
            ->pattern('^[ -~]+$')
            ->minLength(24)
            ->maxLength(255)
            ->validate();

        $this->password = $password;

        return $this;
    }

    public function getQuota(): ?int
    {
        return $this->quota;
    }

    public function setQuota(?int $quota): self
    {
        $this->quota = $quota;

        return $this;
    }

    public function getMailDomainId(): int
    {
        return $this->mailDomainId;
    }

    public function setMailDomainId(int $mailDomainId): self
    {
        $this->mailDomainId = $mailDomainId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): self
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): self
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): self
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): self
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): self
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
