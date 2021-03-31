<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Command extends ClusterModel implements Model
{
    private string $command;
    private array $secretValues = [];
    private ?int $virtualHostId;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?int $returnCode = null;
    private ?string $standardOut = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getCommand(): string
    {
        return $this->command;
    }

    public function setCommand(string $command): Command
    {
        $this->command = $command;

        return $this;
    }

    public function getSecretValues(): array
    {
        return $this->secretValues;
    }

    public function setSecretValues(array $secretValues): Command
    {
        $this->secretValues = $secretValues;

        return $this;
    }

    public function getVirtualHostId(): ?int
    {
        return $this->virtualHostId;
    }

    public function setVirtualHostId(?int $virtualHostId): Command
    {
        $this->virtualHostId = $virtualHostId;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): Command
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): Command
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getReturnCode(): ?int
    {
        return $this->returnCode;
    }

    public function setReturnCode(?int $returnCode): Command
    {
        $this->returnCode = $returnCode;

        return $this;
    }

    public function getStandardOut(): ?string
    {
        return $this->standardOut;
    }

    public function setStandardOut(?string $standardOut): Command
    {
        $this->standardOut = $standardOut;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): Command
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): Command
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): Command
    {
        return $this
            ->setCommand(Arr::get($data, 'command'))
            ->setSecretValues(Arr::get($data, 'secret_values', []))
            ->setVirtualHostId(Arr::get($data, 'virtual_host_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setReturnCode(Arr::get($data, 'return_code'))
            ->setStandardOut(Arr::get($data, 'standard_out'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'command' => $this->getCommand(),
            'secret_values' => $this->getSecretValues(),
            'virtual_host_id' => $this->getVirtualHostId(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'return_code' => $this->getReturnCode(),
            'standard_out' => $this->getStandardOut(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
