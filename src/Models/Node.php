<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\NodeGroup;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class Node extends ClusterModel
{
    private string $hostname;
    private array $groups = [];
    private ?string $comment = null;
    private array $loadBalancerHealthChecksGroupsPairs = [];
    private array $groupProperties = [];
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getHostname(): string
    {
        return $this->hostname;
    }

    public function setHostname(string $hostname): self
    {
        $this->hostname = $hostname;

        return $this;
    }

    public function getGroups(): ?array
    {
        return $this->groups;
    }

    public function setGroups(array $groups): self
    {
        $this->groups = $groups;

        return $this;
    }

    public function getComment(): ?string
    {
        return $this->comment;
    }

    public function setComment(?string $comment): self
    {
        Validator::value($comment)
            ->nullable()
            ->maxLength(255)
            ->validate();

        $this->comment = $comment;

        return $this;
    }

    /**
     * @return array<string, array<NodeGroup>>
     */
    public function getLoadBalancerHealthChecksGroupsPairs(): array
    {
        return $this->loadBalancerHealthChecksGroupsPairs;
    }

    /**
     * @param array<string, array<NodeGroup>> $loadBalancerHealthChecksGroupsPairs
     */
    public function setLoadBalancerHealthChecksGroupsPairs(array $loadBalancerHealthChecksGroupsPairs): self
    {
        $this->loadBalancerHealthChecksGroupsPairs = $loadBalancerHealthChecksGroupsPairs;

        return $this;
    }

    public function getGroupProperties(): array
    {
        return $this->groupProperties;
    }

    public function setGroupProperties(array $groupProperties): self
    {
        $this->groupProperties = $groupProperties;

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
            ->setHostname(Arr::get($data, 'hostname'))
            ->setGroups(Arr::get($data, 'groups', []))
            ->setComment(Arr::get($data, 'comment'))
            ->setLoadBalancerHealthChecksGroupsPairs(Arr::get($data, 'load_balancer_health_checks_groups_pairs', []))
            ->setGroupProperties(Arr::get($data, 'group_properties', []))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'hostname' => $this->getHostname(),
            'groups' => $this->getGroups(),
            'comment' => $this->getComment(),
            'load_balancer_health_checks_groups_pairs' => $this->getLoadBalancerHealthChecksGroupsPairs(),
            'group_properties' => $this->getGroupProperties(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
