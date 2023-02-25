<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\AllowOverrideDirectives;
use Cyberfusion\ClusterApi\Enums\AllowOverrideOptionDirectives;
use Cyberfusion\ClusterApi\Enums\VirtualHostServerSoftwareName;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class VirtualHost extends ClusterModel
{
    private string $domain;
    private array $serverAliases = [];
    private int $unixUserId;
    private string $documentRoot;
    private string $publicRoot;
    private ?int $fpmPoolId = null;
    private ?int $passengerAppId = null;
    private ?string $customConfig = null;
    private ?string $serverSoftwareName = null;
    private ?string $domainRoot = null;
    private ?array $allowOverrideDirectives;
    private ?array $allowOverrideOptionDirectives;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getDomain(): string
    {
        return $this->domain;
    }

    public function setDomain(string $domain): self
    {
        $this->domain = $domain;

        return $this;
    }

    public function getServerAliases(): array
    {
        return $this->serverAliases;
    }

    public function setServerAliases(array $serverAliases): self
    {
        Validator::value($serverAliases)
            ->unique()
            ->validate();

        $this->serverAliases = $serverAliases;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): self
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getDocumentRoot(): string
    {
        return $this->documentRoot;
    }

    public function setDocumentRoot(string $documentRoot): self
    {
        Validator::value($documentRoot)
            ->path()
            ->validate();

        $this->documentRoot = $documentRoot;

        return $this;
    }

    public function getPublicRoot(): string
    {
        return $this->publicRoot;
    }

    public function setPublicRoot(string $publicRoot): self
    {
        Validator::value($publicRoot)
            ->path()
            ->validate();

        $this->publicRoot = $publicRoot;

        return $this;
    }

    public function getFpmPoolId(): ?int
    {
        return $this->fpmPoolId;
    }

    public function setFpmPoolId(?int $fpmPoolId): self
    {
        $this->fpmPoolId = $fpmPoolId;

        return $this;
    }

    public function getPassengerAppId(): ?int
    {
        return $this->passengerAppId;
    }

    public function setPassengerAppId(?int $passengerAppId): self
    {
        $this->passengerAppId = $passengerAppId;

        return $this;
    }

    public function getCustomConfig(): ?string
    {
        return $this->customConfig;
    }

    public function setCustomConfig(?string $customConfig): self
    {
        Validator::value($customConfig)
            ->nullable()
            ->maxLength(65535)
            ->pattern('^[ -~\n]+$')
            ->validate();

        $this->customConfig = $customConfig;

        return $this;
    }

    public function getServerSoftwareName(): string
    {
        return $this->serverSoftwareName;
    }

    public function setServerSoftwareName(string $serverSoftwareName): self
    {
        Validator::value($serverSoftwareName)
            ->valueIn(VirtualHostServerSoftwareName::AVAILABLE)
            ->validate();

        $this->serverSoftwareName = $serverSoftwareName;

        return $this;
    }

    public function getDomainRoot(): ?string
    {
        return $this->domainRoot;
    }

    public function setDomainRoot(?string $domainRoot): self
    {
        Validator::value($domainRoot)
            ->nullable()
            ->path()
            ->validate();

        $this->domainRoot = $domainRoot;

        return $this;
    }

    public function getAllowOverrideDirectives(): ?array
    {
        if ($this->getServerSoftwareName() === VirtualHostServerSoftwareName::SERVER_SOFTWARE_NGINX) {
            return null;
        }

        if (is_null($this->allowOverrideDirectives)) {
            return AllowOverrideDirectives::DEFAULTS;
        }

        return $this->allowOverrideDirectives;
    }

    public function setAllowOverrideDirectives(?array $allowOverrideDirectives): self
    {
        Validator::value($allowOverrideDirectives)
            ->nullable()
            ->valuesIn(AllowOverrideDirectives::AVAILABLE)
            ->unique()
            ->validate();

        $this->allowOverrideDirectives = $allowOverrideDirectives;

        return $this;
    }

    public function getAllowOverrideOptionDirectives(): ?array
    {
        if ($this->getServerSoftwareName() === VirtualHostServerSoftwareName::SERVER_SOFTWARE_NGINX) {
            return null;
        }

        if (is_null($this->allowOverrideOptionDirectives)) {
            return AllowOverrideOptionDirectives::DEFAULTS;
        }

        return $this->allowOverrideOptionDirectives;
    }

    public function setAllowOverrideOptionDirectives(?array $allowOverrideOptionDirectives): self
    {
        Validator::value($allowOverrideOptionDirectives)
            ->nullable()
            ->valuesIn(AllowOverrideOptionDirectives::AVAILABLE)
            ->unique()
            ->validate();

        $this->allowOverrideOptionDirectives = $allowOverrideOptionDirectives;

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
            ->setDomain(Arr::get($data, 'domain'))
            ->setServerAliases(Arr::get($data, 'server_aliases', []))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setDocumentRoot(Arr::get($data, 'document_root'))
            ->setPublicRoot(Arr::get($data, 'public_root'))
            ->setFpmPoolId(Arr::get($data, 'fpm_pool_id'))
            ->setPassengerAppId(Arr::get($data, 'passenger_app_id'))
            ->setDomainRoot(Arr::get($data, 'domain_root'))
            ->setCustomConfig(Arr::get($data, 'custom_config'))
            ->setAllowOverrideDirectives(Arr::get($data, 'allow_override_directives'))
            ->setAllowOverrideOptionDirectives(Arr::get($data, 'allow_override_option_directives'))
            ->setServerSoftwareName(Arr::get($data, 'server_software_name'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'domain' => $this->getDomain(),
            'server_aliases' => $this->getServerAliases(),
            'unix_user_id' => $this->getUnixUserId(),
            'document_root' => $this->getDocumentRoot(),
            'public_root' => $this->getPublicRoot(),
            'fpm_pool_id' => $this->getFpmPoolId(),
            'passenger_app_id' => $this->getPassengerAppId(),
            'custom_config' => $this->getCustomConfig(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'domain_root' => $this->getDomainRoot(),
            'allow_override_directives' => $this->getAllowOverrideDirectives(),
            'allow_override_option_directives' => $this->getAllowOverrideOptionDirectives(),
            'server_software_name' => $this->getServerSoftwareName(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
