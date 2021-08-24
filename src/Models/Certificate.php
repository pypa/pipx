<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Certificate extends ClusterModel implements Model
{
    private string $mainCommonName = '';
    private array $commonNames = [];
    private ?string $certificate = null;
    private ?string $caChain = null;
    private ?string $privateKey = null;
    private ?int $id = null;
    private ?string $statusMessage = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getMainCommonName(): string
    {
        return $this->mainCommonName;
    }

    public function setMainCommonName(string $mainCommonName): Certificate
    {
        $this->mainCommonName = $mainCommonName;

        return $this;
    }

    public function getCommonNames(): array
    {
        return $this->commonNames;
    }

    public function setCommonNames(array $commonNames): Certificate
    {
        $this->commonNames = $commonNames;

        return $this;
    }

    public function getCertificate(): ?string
    {
        return $this->certificate;
    }

    public function setCertificate(?string $certificate): Certificate
    {
        $this->certificate = $certificate;

        return $this;
    }

    public function getCaChain(): ?string
    {
        return $this->caChain;
    }

    public function setCaChain(?string $caChain): Certificate
    {
        $this->caChain = $caChain;

        return $this;
    }

    public function getPrivateKey(): ?string
    {
        return $this->privateKey;
    }

    public function setPrivateKey(?string $privateKey): Certificate
    {
        $this->privateKey = $privateKey;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): Certificate
    {
        $this->id = $id;

        return $this;
    }

    public function getStatusMessage(): ?string
    {
        return $this->statusMessage;
    }

    public function setStatusMessage(?string $statusMessage): Certificate
    {
        $this->statusMessage = $statusMessage;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): Certificate
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): Certificate
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): Certificate
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): Certificate
    {
        return $this
            ->setMainCommonName(Arr::get($data, 'main_common_name', ''))
            ->setCommonNames(Arr::get($data, 'common_names', []))
            ->setCertificate(Arr::get($data, 'certificate'))
            ->setCaChain(Arr::get($data, 'ca_chain'))
            ->setPrivateKey(Arr::get($data, 'private_key'))
            ->setId(Arr::get($data, 'id'))
            ->setStatusMessage(Arr::get($data, 'status_message'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'main_common_name' => $this->getMainCommonName(),
            'common_names' => $this->getCommonNames(),
            'certificate' => $this->getCertificate(),
            'ca_chain' => $this->getCaChain(),
            'private_key' => $this->getPrivateKey(),
            'id' => $this->getId(),
            'status_message' => $this->getStatusMessage(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }

    public function isLetsEncrypt(): bool
    {
        return count($this->commonNames) !== 0;
    }
}
