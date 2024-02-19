<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\FirewallRuleExternalProviderName;
use Cyberfusion\ClusterApi\Enums\FirewallRuleServiceName;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class FirewallRule extends ClusterModel
{
    private ?int $nodeId = null;
    private ?int $firewallGroupId = null;
    private ?string $externalProviderName = null;
    private ?string $serviceName = null;
    private ?int $haproxyListenId = null;
    private ?int $port = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getNodeId(): ?int
    {
        return $this->nodeId;
    }

    public function setNodeId(?int $nodeId): self
    {
        Validator::value($nodeId)
            ->minAmount(1)
            ->nullable()
            ->validate();

        $this->nodeId = $nodeId;
        return $this;
    }

    public function getFirewallGroupId(): ?int
    {
        return $this->firewallGroupId;
    }

    public function setFirewallGroupId(?int $firewallGroupId): self
    {
        $this->firewallGroupId = $firewallGroupId;
        return $this;
    }

    public function getExternalProviderName(): ?string
    {
        return $this->externalProviderName;
    }

    public function setExternalProviderName(?string $externalProviderName): self
    {
        Validator::value($externalProviderName)
            ->valueIn(FirewallRuleExternalProviderName::AVAILABLE)
            ->nullable()
            ->validate();

        $this->externalProviderName = $externalProviderName;
        return $this;
    }

    public function getServiceName(): ?string
    {
        return $this->serviceName;
    }

    public function setServiceName(?string $serviceName): self
    {
        Validator::value($serviceName)
            ->valueIn(FirewallRuleServiceName::AVAILABLE)
            ->nullable()
            ->validate();

        $this->serviceName = $serviceName;
        return $this;
    }

    public function getHaproxyListenId(): ?int
    {
        return $this->haproxyListenId;
    }

    public function setHaproxyListenId(?int $haproxyListenId): self
    {
        Validator::value($haproxyListenId)
            ->minAmount(1)
            ->nullable()
            ->validate();

        $this->haproxyListenId = $haproxyListenId;
        return $this;
    }

    public function getPort(): ?int
    {
        return $this->port;
    }

    public function setPort(?int $port): self
    {
        Validator::value($port)
            ->minAmount(1)
            ->maxAmount(65535)
            ->nullable()
            ->validate();

        $this->port = $port;
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
            ->setNodeId(Arr::get($data, 'node_id'))
            ->setFirewallGroupId(Arr::get($data, 'firewall_group_id'))
            ->setExternalProviderName(Arr::get($data, 'external_provider_name'))
            ->setServiceName(Arr::get($data, 'service_name'))
            ->setHaproxyListenId(Arr::get($data, 'haproxy_listen_id'))
            ->setPort(Arr::get($data, 'port'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'node_id' => $this->getNodeId(),
            'firewall_group_id' => $this->getFirewallGroupId(),
            'external_provider_name' => $this->getExternalProviderName(),
            'service_name' => $this->getServiceName(),
            'haproxy_listen_id' => $this->getHaproxyListenId(),
            'port' => $this->getPort(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
