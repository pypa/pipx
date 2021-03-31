<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class VirtualHost extends ClusterModel implements Model
{
    private string $domain;
    private array $serverAliases = [];
    private int $unixUserId;
    private string $documentRoot;
    private string $publicRoot;
    private ?int $fpmPoolId = null;
    private bool $forceSsl = true;
    private ?string $customConfig = null;
    private ?string $balancerBackendName = null;
    private array $deployCommands = [];
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getDomain(): string
    {
        return $this->domain;
    }

    public function setDomain(string $domain): VirtualHost
    {
        $this->domain = $domain;

        return $this;
    }

    public function getServerAliases(): array
    {
        return $this->serverAliases;
    }

    public function setServerAliases(array $serverAliases): VirtualHost
    {
        $this->serverAliases = $serverAliases;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): VirtualHost
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getDocumentRoot(): string
    {
        return $this->documentRoot;
    }

    public function setDocumentRoot(string $documentRoot): VirtualHost
    {
        $this->documentRoot = $documentRoot;

        return $this;
    }

    public function getPublicRoot(): string
    {
        return $this->publicRoot;
    }

    public function setPublicRoot(string $publicRoot): VirtualHost
    {
        $this->publicRoot = $publicRoot;

        return $this;
    }

    public function getFpmPoolId(): ?int
    {
        return $this->fpmPoolId;
    }

    public function setFpmPoolId(?int $fpmPoolId): VirtualHost
    {
        $this->fpmPoolId = $fpmPoolId;

        return $this;
    }

    public function isForceSsl(): bool
    {
        return $this->forceSsl;
    }

    public function setForceSsl(bool $forceSsl): VirtualHost
    {
        $this->forceSsl = $forceSsl;

        return $this;
    }

    public function getCustomConfig(): ?string
    {
        return $this->customConfig;
    }

    public function setCustomConfig(?string $customConfig): VirtualHost
    {
        $this->customConfig = $customConfig;

        return $this;
    }

    public function getBalancerBackendName(): ?string
    {
        return $this->balancerBackendName;
    }

    public function setBalancerBackendName(?string $balancerBackendName): VirtualHost
    {
        $this->validate($balancerBackendName, [
            'length_max' => 64,
            'pattern' => '^[a-z0-9-_.]+$',
        ]);

        $this->balancerBackendName = $balancerBackendName;

        return $this;
    }

    public function getDeployCommands(): array
    {
        return $this->deployCommands;
    }

    public function setDeployCommands(array $deployCommands): VirtualHost
    {
        $this->deployCommands = $deployCommands;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): VirtualHost
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): VirtualHost
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): VirtualHost
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): VirtualHost
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): VirtualHost
    {
        return $this
            ->setDomain(Arr::get($data, 'domain'))
            ->setServerAliases(Arr::get($data, 'server_aliases', []))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setDocumentRoot(Arr::get($data, 'document_root'))
            ->setPublicRoot(Arr::get($data, 'public_root'))
            ->setFpmPoolId(Arr::get($data, 'fpm_pool_id'))
            ->setForceSsl(Arr::get($data, 'force_ssl'))
            ->setBalancerBackendName(Arr::get($data, 'balancer_backend_name'))
            ->setCustomConfig(Arr::get($data, 'custom_config'))
            ->setDeployCommands(Arr::get($data, 'deploy_commands', []))
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
            'force_ssl' => $this->isForceSsl(),
            'custom_config' => $this->getCustomConfig(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'balancer_backend_name' => $this->getBalancerBackendName(),
            'deploy_commands' => $this->getDeployCommands(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
