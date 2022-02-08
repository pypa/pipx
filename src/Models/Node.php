<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Support\Validator;

class Node extends ClusterModel implements Model
{
    private string $hostname;
    private array $groups = [];
    private ?string $comment = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getHostname(): string
    {
        return $this->hostname;
    }

    public function setHostname(string $hostname): Node
    {
        $this->hostname = $hostname;

        return $this;
    }

    public function getGroups(): ?array
    {
        return $this->groups;
    }

    public function setGroups(array $groups): Node
    {
        $this->groups = $groups;

        return $this;
    }

    public function getComment(): ?string
    {
        return $this->comment;
    }

    public function setComment(?string $comment): Node
    {
        Validator::value($comment)
            ->nullable()
            ->maxLength(255)
            ->validate();

        $this->comment = $comment;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): Node
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): Node
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): Node
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): Node
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): Node
    {
        return $this
            ->setHostname(Arr::get($data, 'hostname'))
            ->setGroups(Arr::get($data, 'groups', []))
            ->setComment(Arr::get($data, 'comment'))
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
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
