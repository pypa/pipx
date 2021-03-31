<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class MailDomain extends ClusterModel implements Model
{
    private string $domain;
    private array $catchAllForwardEmailAddresses = [];
    private bool $isLocal = true;
    private int $unixUserId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getDomain(): string
    {
        return $this->domain;
    }

    public function setDomain(string $domain): MailDomain
    {
        $this->domain = $domain;

        return $this;
    }

    public function getCatchAllForwardEmailAddresses(): array
    {
        return $this->catchAllForwardEmailAddresses;
    }

    public function setCatchAllForwardEmailAddresses(array $catchAllForwardEmailAddresses): MailDomain
    {
        $this->catchAllForwardEmailAddresses = $catchAllForwardEmailAddresses;

        return $this;
    }

    public function isLocal(): bool
    {
        return $this->isLocal;
    }

    public function setIsLocal(bool $isLocal): MailDomain
    {
        $this->isLocal = $isLocal;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): MailDomain
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): MailDomain
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): MailDomain
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): MailDomain
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): MailDomain
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): MailDomain
    {
        return $this
            ->setDomain(Arr::get($data, 'domain'))
            ->setCatchAllForwardEmailAddresses(Arr::get($data, 'catch_all_forward_email_addresses', []))
            ->setIsLocal(Arr::get($data, 'is_local'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'domain' => $this->getDomain(),
            'catch_all_forward_email_addresses' => $this->getCatchAllForwardEmailAddresses(),
            'is_local' => $this->isLocal(),
            'unix_user_id' => $this->getUnixUserId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
