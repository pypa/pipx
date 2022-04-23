<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Enums\TaskState;
use Vdhicts\Cyberfusion\ClusterApi\Support\Validator;

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

    public function setUuid(string $uuid): TaskResult
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

    public function setDescription(string $description): TaskResult
    {
        Validator::value($description)
            ->minLength(1)
            ->maxLength(65535)
            ->validate();

        $this->description = $description;

        return $this;
    }

    public function getMessage(): string
    {
        return $this->message;
    }

    public function setMessage(string $message): TaskResult
    {
        Validator::value($message)
            ->minLength(1)
            ->maxLength(65535)
            ->validate();

        $this->message = $message;

        return $this;
    }

    public function getState(): string
    {
        return $this->state;
    }

    public function setState(string $state): TaskResult
    {
        Validator::value($state)
            ->valueIn(TaskState::AVAILABLE)
            ->validate();

        $this->state = $state;

        return $this;
    }

    public function fromArray(array $data): TaskResult
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
