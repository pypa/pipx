<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class ValidationError extends ClusterModel implements Model
{
    private array $location = [];
    private string $message;
    private string $type;

    public function getLocation(): array
    {
        return $this->location;
    }

    public function setLocation(array $location): ValidationError
    {
        $this->location = $location;

        return $this;
    }

    public function getMessage(): string
    {
        return $this->message;
    }

    public function setMessage(string $message): ValidationError
    {
        $this->message = $message;

        return $this;
    }

    public function getType(): string
    {
        return $this->type;
    }

    public function setType(string $type): ValidationError
    {
        $this->type = $type;

        return $this;
    }

    public function fromArray(array $data): ValidationError
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
