<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;

class ValidationError extends ClusterModel implements Model
{
    private array $location = [];
    private string $message;
    private string $type;

    public function getLocation(): array
    {
        return $this->location;
    }

    public function setLocation(array $location): self
    {
        $this->location = $location;

        return $this;
    }

    public function getMessage(): string
    {
        return $this->message;
    }

    public function setMessage(string $message): self
    {
        $this->message = $message;

        return $this;
    }

    public function getType(): string
    {
        return $this->type;
    }

    public function setType(string $type): self
    {
        $this->type = $type;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setLocation(Arr::get($data, 'loc', []))
            ->setMessage(Arr::get($data, 'msg'))
            ->setType(Arr::get($data, 'type'));
    }

    public function toArray(): array
    {
        return [
            'loc' => $this->getLocation(),
            'msg' => $this->getMessage(),
            'type' => $this->getType(),
        ];
    }
}
