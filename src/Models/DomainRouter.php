<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\DomainRouterCategory;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class DomainRouter extends ClusterModel
{
    private string $domain;
    private bool $forceSsl = true;
    private ?int $virtualHostId = null;
    private ?int $urlRedirectId = null;
    private ?int $nodeId = null;
    private ?int $certificateId = null;
    private ?int $securityTxtPolicyId = null;
    private array $firewallGroupsIds = [];
    private ?string $category = null;
    private int $id;
    private int $clusterId;
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

    public function isForceSsl(): bool
    {
        return $this->forceSsl;
    }

    public function setForceSsl(bool $forceSsl): self
    {
        $this->forceSsl = $forceSsl;

        return $this;
    }

    public function getVirtualHostId(): ?int
    {
        return $this->virtualHostId;
    }

    public function setVirtualHostId(?int $virtualHostId): self
    {
        $this->virtualHostId = $virtualHostId;

        return $this;
    }

    public function getUrlRedirectId(): ?int
    {
        return $this->urlRedirectId;
    }

    public function setUrlRedirectId(?int $urlRedirectId): self
    {
        $this->urlRedirectId = $urlRedirectId;

        return $this;
    }

    public function getNodeId(): ?int
    {
        return $this->nodeId;
    }

    public function setNodeId(?int $nodeId): self
    {
        $this->nodeId = $nodeId;

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

    public function getFirewallGroupsIds(): array
    {
        return $this->firewallGroupsIds;
    }

    public function setFirewallGroupsIds(array $firewallGroupIds): self
    {
        $this->firewallGroupsIds = $firewallGroupIds;
        return $this;
    }

    public function getCategory(): ?string
    {
        return $this->category;
    }

    public function setCategory(?string $category): self
    {
        Validator::value($category)
            ->valueIn(DomainRouterCategory::AVAILABLE)
            ->nullable()
            ->validate();

        $this->category = $category;
        return $this;
    }

    public function getId(): int
    {
        return $this->id;
    }

    public function setId(int $id): self
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): self
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

    public function getSecurityTxtPolicyId(): ?int
    {
        return $this->securityTxtPolicyId;
    }

    public function setSecurityTxtPolicyId(?int $securityTxtPolicyId): self
    {
        $this->securityTxtPolicyId = $securityTxtPolicyId;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setDomain(Arr::get($data, 'domain'))
            ->setForceSsl(Arr::get($data, 'force_ssl'))
            ->setVirtualHostId(Arr::get($data, 'virtual_host_id'))
            ->setUrlRedirectId(Arr::get($data, 'url_redirect_id'))
            ->setNodeId(Arr::get($data, 'node_id'))
            ->setCertificateId(Arr::get($data, 'certificate_id'))
            ->setFirewallGroupsIds(Arr::get($data, 'firewall_group_ids', []))
            ->setCategory(Arr::get($data, 'category'))
            ->setId(Arr::get($data, 'id'))
            ->setSecurityTxtPolicyId(Arr::get($data, 'security_txt_policy_id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'domain' => $this->getDomain(),
            'force_ssl' => $this->isForceSsl(),
            'virtual_host_id' => $this->getVirtualHostId(),
            'url_redirect_id' => $this->getUrlRedirectId(),
            'node_id' => $this->getNodeId(),
            'certificate_id' => $this->getCertificateId(),
            'id' => $this->getId(),
            'security_txt_policy_id' => $this->getSecurityTxtPolicyId(),
            'firewall_groups_ids' => $this->getFirewallGroupsIds(),
            'category' => $this->getCategory(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
