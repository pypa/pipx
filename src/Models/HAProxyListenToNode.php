<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;

class HAProxyListenToNode extends ClusterModel
{
    private int $haProxyListenId;

    private int $nodeId;

    private int $clusterId;

    private ?int $id = null;

    private ?string $createdAt = null;

    private ?string $updatedAt = null;

    public function getHaProxyListenId(): int
    {
        return $this->haProxyListenId;
    }

    public function setHaProxyListenId(int $haProxyListenId): self
    {
        $this->haProxyListenId = $haProxyListenId;

        return $this;
    }

    public function getNodeId(): int
    {
        return $this->nodeId;
    }

    public function setNodeId(int $nodeId): self
    {
        $this->nodeId = $nodeId;

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

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): self
    {
        $this->id = $id;

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
            ->setHaProxyListenId(Arr::get($data, 'ha_proxy_listen_id'))
            ->setNodeId(Arr::get($data, 'node_id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setId(Arr::get($data, 'id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'haproxy_listen_id' => $this->getHaProxyListenId(),
            'node_id' => $this->getNodeId(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
