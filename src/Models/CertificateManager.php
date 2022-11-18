<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\ProviderNames;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;

class CertificateManager extends ClusterModel implements Model
{
    private ?string $mainCommonName = '';
    private array $commonNames = [];
    private string $providerName;
    private ?string $requestCallbackUrl = null;
    private ?int $certificateId = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getMainCommonName(): ?string
    {
        return $this->mainCommonName;
    }

    public function setMainCommonName(?string $mainCommonName): CertificateManager
    {
        $this->mainCommonName = $mainCommonName;

        return $this;
    }

    public function getCommonNames(): array
    {
        return $this->commonNames;
    }

    public function setCommonNames(array $commonNames): CertificateManager
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

    public function setProviderName(string $providerName): CertificateManager
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

    public function setRequestCallbackUrl(?string $requestCallbackUrl): CertificateManager
    {
        $this->requestCallbackUrl = $requestCallbackUrl;

        return $this;
    }

    public function getCertificateId(): ?int
    {
        return $this->certificateId;
    }

    public function setCertificateId(?int $certificateId): CertificateManager
    {
        $this->certificateId = $certificateId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): CertificateManager
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): CertificateManager
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): CertificateManager
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): CertificateManager
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): CertificateManager
    {
        return $this
            ->setMainCommonName(Arr::get($data, 'main_common_name', ''))
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
