<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class BorgArchiveUnixUserCreation extends ClusterModel implements Model
{
    private string $name;
    private int $unixUserId;
    private int $borgRepositoryId;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): self
    {
        Validator::value($name)
            ->maxLength(64)
            ->pattern('^[a-zA-Z0-9-_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): self
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getBorgRepositoryId(): int
    {
        return $this->borgRepositoryId;
    }

    public function setBorgRepositoryId(int $borgRepositoryId): self
    {
        $this->borgRepositoryId = $borgRepositoryId;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setBorgRepositoryId(Arr::get($data, 'borg_repository_id'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'unix_user_id' => $this->getUnixUserId(),
            'borg_repository_id' => $this->getBorgRepositoryId(),
        ];
    }
}
