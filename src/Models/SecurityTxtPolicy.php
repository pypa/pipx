<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class SecurityTxtPolicy extends ClusterModel
{
    private string $expiresTimestamp;
    private array $emailContacts = [];
    private array $urlContacts = [];
    private array $encryptingKeyUrls = [];
    private array $acknowledgementUrls = [];
    private array $policyUrls = [];
    private array $openingUrls = [];
    private array $preferredLanguages = [];
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getExpiresTimestamp(): string
    {
        return $this->expiresTimestamp;
    }

    public function setExpiresTimestamp(string $expiresTimestamp): self
    {
        $this->expiresTimestamp = $expiresTimestamp;
        return $this;
    }

    public function getEmailContacts(): array
    {
        return $this->emailContacts;
    }

    public function setEmailContacts(array $emailContacts): self
    {
        Validator::value($emailContacts)
            ->unique()
            ->validate();

        $this->emailContacts = $emailContacts;
        return $this;
    }

    public function getUrlContacts(): array
    {
        return $this->urlContacts;
    }

    public function setUrlContacts(array $urlContacts): self
    {
        Validator::value($urlContacts)
            ->unique()
            ->validate();

        $this->urlContacts = $urlContacts;
        return $this;
    }

    public function getEncryptingKeyUrls(): array
    {
        return $this->encryptingKeyUrls;
    }

    public function setEncryptingKeyUrls(array $encryptingKeyUrls): self
    {
        Validator::value($encryptingKeyUrls)
            ->unique()
            ->validate();

        $this->encryptingKeyUrls = $encryptingKeyUrls;
        return $this;
    }

    public function getAcknowledgementUrls(): array
    {
        return $this->acknowledgementUrls;
    }

    public function setAcknowledgementUrls(array $acknowledgementUrls): self
    {
        Validator::value($acknowledgementUrls)
            ->unique()
            ->validate();

        $this->acknowledgementUrls = $acknowledgementUrls;
        return $this;
    }

    public function getPolicyUrls(): array
    {
        return $this->policyUrls;
    }

    public function setPolicyUrls(array $policyUrls): self
    {
        Validator::value($policyUrls)
            ->unique()
            ->validate();

        $this->policyUrls = $policyUrls;
        return $this;
    }

    public function getOpeningUrls(): array
    {
        return $this->openingUrls;
    }

    public function setOpeningUrls(array $openingUrls): self
    {
        Validator::value($openingUrls)
            ->unique()
            ->validate();

        $this->openingUrls = $openingUrls;
        return $this;
    }

    public function getPreferredLanguages(): array
    {
        return $this->preferredLanguages;
    }

    public function setPreferredLanguages(array $preferredLanguages): self
    {
        Validator::value($preferredLanguages)
            ->unique()
            ->validate();

        $this->preferredLanguages = $preferredLanguages;
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
            ->setExpiresTimestamp(Arr::get($data, 'expires_timestamp'))
            ->setEmailContacts(Arr::get($data, 'email_contacts'))
            ->setUrlContacts(Arr::get($data, 'url_contacts'))
            ->setEncryptingKeyUrls(Arr::get($data, 'encrypting_key_urls'))
            ->setAcknowledgementUrls(Arr::get($data, 'acknowledgement_urls'))
            ->setPolicyUrls(Arr::get($data, 'policy_urls'))
            ->setOpeningUrls(Arr::get($data, 'opening_urls'))
            ->setPreferredLanguages(Arr::get($data, 'preferred_languages'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'expires_timestamp' => $this->getExpiresTimestamp(),
            'email_contacts' => $this->getEmailContacts(),
            'url_contacts' => $this->getUrlContacts(),
            'encrypting_key_urls' => $this->getEncryptingKeyUrls(),
            'acknowledgement_urls' => $this->getAcknowledgementUrls(),
            'policy_urls' => $this->getPolicyUrls(),
            'opening_urls' => $this->getOpeningUrls(),
            'preferred_languages' => $this->getPreferredLanguages(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
