<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class Site extends ClusterModel
{
    private ?int $id = null;
    private ?string $name = null;

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): self
    {
        $this->id = $id;
        return $this;
    }

    public function getName(): ?string
    {
        return $this->name;
    }

    public function setName(?string $name): self
    {
        Validator::value($name)
            ->minLength(1)
            ->maxLength(32)
            ->pattern('^[A-Z0-9-]+$')
            ->nullable()
            ->validate();

        $this->name = $name;
        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setId(Arr::get($data, 'id'))
            ->setName(Arr::get($data, 'name'));
    }

    public function toArray(): array
    {
        return [
            'id' => $this->getId(),
            'name' => $this->getName(),
        ];
    }
}
