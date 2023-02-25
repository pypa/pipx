<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\ProviderNames;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class CertificateManager extends ClusterModel
{
    private ?string $mainCommonName = '';
    private array $commonNames = [];
    private string $providerName;
    private ?string $requestCallbackUrl = null;
    private ?int $certificateId = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $lastRequestTaskCollectionUuid = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getMainCommonName(): ?string
    {
        return $this->mainCommonName;
    }

    public function setMainCommonName(?string $mainCommonName): self
    {
        $this->mainCommonName = $mainCommonName;

        return $this;
    }

    public function getLastRequestTaskCollectionUuid(): ?string
    {
        return $this->lastRequestTaskCollectionUuid;
    }

    public function setLastRequestTaskCollectionUuid(?string $lastRequestTaskCollectionUuid): self
    {
        $this->lastRequestTaskCollectionUuid = $lastRequestTaskCollectionUuid;

        return $this;
    }

    public function getCommonNames(): array
    {
        return $this->commonNames;
    }

    public function setCommonNames(array $commonNames): self
    {
        Validator::value($commonNames)
            ->unique()
            ->validate();

        $this->commonNames = array_unique($commonNames);

        return $this;
    }

    public function getProviderName(): string
    {
        return $this->providerName;
    }

    public function setProviderName(string $providerName): self
    {
        Validator::value($providerName)
            ->valueIn(ProviderNames::AVAILABLE)
            ->validate();

        $this->providerName = $providerName;

        return $this;
    }

    public function getRequestCallbackUrl(): ?string
    {
        return $this->requestCallbackUrl;
    }

    public function setRequestCallbackUrl(?string $requestCallbackUrl): self
    {
        $this->requestCallbackUrl = $requestCallbackUrl;

        return $this;
    }

    public function getCertificateId(): ?int
    {
        return $this->certificateId;
    }

    public function setCertificateId(?int $certificateId): self
    {
        $this->certificateId = $certificateId;

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
            ->setMainCommonName(Arr::get($data, 'main_common_name', ''))
            ->setLastRequestTaskCollectionUuid(Arr::get($data, 'last_request_task_collection_uuid'))
            ->setCommonNames(Arr::get($data, 'common_names', []))
            ->setProviderName(Arr::get($data, 'provider_name'))
            ->setRequestCallbackUrl(Arr::get($data, 'request_callback_url'))
            ->setCertificateId(Arr::get($data, 'certificate_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'main_common_name' => $this->getMainCommonName(),
            'last_request_task_collection_uuid' => $this->getLastRequestTaskCollectionUuid(),
            'common_names' => $this->getCommonNames(),
            'provider_name' => $this->getProviderName(),
            'request_callback_url' => $this->getRequestCallbackUrl(),
            'certificate_id' => $this->getCertificateId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
