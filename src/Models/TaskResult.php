<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Enums\TaskState;
use Cyberfusion\ClusterApi\Support\Validator;
use Illuminate\Support\Arr;

class TaskResult extends ClusterModel implements Model
{
    private string $uuid;
    private string $description;
    private string $message;
    private string $state;

    public function getUuid(): string
    {
        return $this->uuid;
    }

    public function setUuid(string $uuid): self
    {
        Validator::value($uuid)
            ->uuid()
            ->validate();

        $this->uuid = $uuid;

        return $this;
    }

    public function getDescription(): string
    {
        return $this->description;
    }

    public function setDescription(string $description): self
    {
        Validator::value($description)
            ->maxLength(65535)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->description = $description;

        return $this;
    }

    public function getMessage(): string
    {
        return $this->message;
    }

    public function setMessage(string $message): self
    {
        Validator::value($message)
            ->maxLength(65535)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->message = $message;

        return $this;
    }

    public function getState(): string
    {
        return $this->state;
    }

    public function setState(string $state): self
    {
        Validator::value($state)
            ->valueIn(TaskState::AVAILABLE)
            ->validate();

        $this->state = $state;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setUuid(Arr::get($data, 'uuid'))
            ->setDescription(Arr::get($data, 'description'))
            ->setMessage(Arr::get($data, 'message'))
            ->setState(Arr::get($data, 'state'));
    }

    public function toArray(): array
    {
        return [
            'uuid' => $this->getUuid(),
            'description' => $this->getDescription(),
            'message' => $this->getMessage(),
            'state' => $this->getState(),
        ];
    }
}
