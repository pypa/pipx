<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\NodeGroup;
use Cyberfusion\ClusterApi\Exceptions\ValidationException;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class HAProxyListen extends ClusterModel
{
    private string $name;

    private string $nodesGroup;

    private ?string $nodesIds = null;

    private ?int $port = null;

    private ?string $socketPath = null;

    private int $destinationClusterId;

    private int $clusterId;

    private ?int $id = null;

    private ?string $createdAt = null;

    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): self
    {
        Validator::value($name)
            ->minLength(1)
            ->maxLength(64)
            ->pattern('^[a-z_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getNodesGroup(): string
    {
        return $this->nodesGroup;
    }

    public function setNodesGroup(string $nodesGroup): self
    {
        Validator::value($nodesGroup)
            ->valueIn(NodeGroup::AVAILABLE)
            ->validate();

        $this->nodesGroup = $nodesGroup;

        return $this;
    }

    public function getNodesIds(): ?array
    {
        return $this->nodesIds;
    }

    public function setNodesIds(?array $nodesIds): self
    {
        $this->nodesIds = $nodesIds;

        return $this;
    }

    public function getPort(): ?int
    {
        return $this->port;
    }

    public function setPort(int $port = null): self
    {
        Validator::value($port)
            ->nullable()
            ->validate();
        if ($port !== null && ($port < 3306 || $port > 7700)) {
            ValidationException::validationFailed([
                sprintf(
                    'port must be between 3306 and 7700, %d given',
                    $port
                ),
            ]);
        }

        $this->port = $port;

        return $this;
    }

    public function getSocketPath(): ?string
    {
        return $this->socketPath;
    }

    public function setSocketPath(?string $socketPath): self
    {
        $this->socketPath = $socketPath;

        return $this;
    }

    public function getDestinationClusterId(): int
    {
        return $this->destinationClusterId;
    }

    public function setDestinationClusterId(int $destinationClusterId): self
    {
        $this->destinationClusterId = $destinationClusterId;

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
            ->setName(Arr::get($data, 'name'))
            ->setNodesGroup(Arr::get($data, 'nodes_group'))
            ->setNodesIds(Arr::get($data, 'nodes_ids'))
            ->setPort(Arr::get($data, 'port'))
            ->setSocketPath(Arr::get($data, 'socket_path'))
            ->setDestinationClusterId(Arr::get($data, 'destination_cluster_id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setId(Arr::get($data, 'id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'nodes_group' => $this->getNodesGroup(),
            'nodes_ids' => $this->getNodesIds(),
            'port' => $this->getPort(),
            'socket_path' => $this->getSocketPath(),
            'destination_cluster_id' => $this->getDestinationClusterId(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
