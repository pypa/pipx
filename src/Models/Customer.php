<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class Customer extends ClusterModel
{
    private ?string $teamCode = null;
    private ?int $id = null;
    private ?string $identifier = null;
    private ?string $dnsSubdomain = null;
    private ?bool $isInternal = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getTeamCode(): ?string
    {
        return $this->teamCode;
    }

    public function setTeamCode(?string $teamCode): self
    {
        Validator::value($teamCode)
            ->minLength(4)
            ->maxLength(6)
            ->pattern('^[A-Z0-9]+$')
            ->nullable()
            ->validate();

        $this->teamCode = $teamCode;
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

    public function getIdentifier(): ?string
    {
        return $this->identifier;
    }

    public function setIdentifier(?string $identifier): self
    {
        Validator::value($identifier)
            ->minLength(2)
            ->maxLength(4)
            ->pattern('^[a-z0-9]+$')
            ->nullable()
            ->validate();

        $this->identifier = $identifier;
        return $this;
    }

    public function getDnsSubdomain(): ?string
    {
        return $this->dnsSubdomain;
    }

    public function setDnsSubdomain(?string $dnsSubdomain): self
    {
        $this->dnsSubdomain = $dnsSubdomain;
        return $this;
    }

    public function getIsInternal(): ?bool
    {
        return $this->isInternal;
    }

    public function setIsInternal(?bool $isInternal): self
    {
        $this->isInternal = $isInternal;
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
            ->setTeamCode(Arr::get($data, 'team_code'))
            ->setIdentifier(Arr::get($data, 'identifier'))
            ->setDnsSubdomain(Arr::get($data, 'dns_subdomain'))
            ->setIsInternal(Arr::get($data, 'is_internal'))
            ->setId(Arr::get($data, 'id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'team_code' => $this->getTeamCode(),
            'identifier' => $this->getIdentifier(),
            'dns_subdomain' => $this->getDnsSubdomain(),
            'is_internal' => $this->getIsInternal(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
