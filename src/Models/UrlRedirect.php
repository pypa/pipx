<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\StatusCode;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class UrlRedirect extends ClusterModel
{
    private string $domain;
    private array $serverAliases = [];
    private string $destinationUrl;
    private int $statusCode = StatusCode::MOVED_PERMANENTLY;
    private bool $keepQueryParameters = true;
    private bool $keepPath = true;
    private ?string $description = null;
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

    public function getDestinationUrl(): string
    {
        return $this->destinationUrl;
    }

    public function setDestinationUrl(string $destinationUrl): self
    {
        Validator::value($destinationUrl)
            ->maxLength(2083)
            ->validate();

        $this->destinationUrl = $destinationUrl;

        return $this;
    }

    public function getStatusCode(): int
    {
        return $this->statusCode;
    }

    public function setStatusCode(int $statusCode): self
    {
        Validator::value($statusCode)
            ->valueIn(StatusCode::AVAILABLE)
            ->validate();

        $this->statusCode = $statusCode;

        return $this;
    }

    public function isKeepQueryParameters(): bool
    {
        return $this->keepQueryParameters;
    }

    public function setKeepQueryParameters(bool $keepQueryParameters): self
    {
        $this->keepQueryParameters = $keepQueryParameters;

        return $this;
    }

    public function isKeepPath(): bool
    {
        return $this->keepPath;
    }

    public function setKeepPath(bool $keepPath): self
    {
        $this->keepPath = $keepPath;

        return $this;
    }

    public function getDescription(): ?string
    {
        return $this->description;
    }

    public function setDescription(?string $description): self
    {
        Validator::value($description)
            ->nullable()
            ->maxLength(255)
            ->pattern('^[a-zA-Z0-9-_ ]+$')
            ->validate();

        $this->description = $description;

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
            ->setDestinationUrl(Arr::get($data, 'destination_url'))
            ->setStatusCode(Arr::get($data, 'status_code'))
            ->setKeepQueryParameters(Arr::get($data, 'keep_query_parameters'))
            ->setKeepPath(Arr::get($data, 'keep_path'))
            ->setDescription(Arr::get($data, 'description'))
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
            'destination_url' => $this->getDestinationUrl(),
            'status_code' => $this->getStatusCode(),
            'keep_query_parameters' => $this->isKeepQueryParameters(),
            'keep_path' => $this->isKeepPath(),
            'description' => $this->getDescription(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
