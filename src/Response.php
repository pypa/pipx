<?php

namespace Cyberfusion\ClusterApi;

class Response
{
    public function __construct(private int $statusCode, private string $statusMessage, private array $data = [])
    {
    }

    public function getStatusCode(): int
    {
        return $this->statusCode;
    }

    public function getStatusMessage(): string
    {
        return $this->statusMessage;
    }

    public function isSuccess(): bool
    {
        return $this->statusCode < 300;
    }

    public function getData(?string $attribute = null): mixed
    {
        if ($attribute === null) {
            return $this->data;
        }

        return $this->data[$attribute] ?? null;
    }

    public function setData(array $data): self
    {
        $this->data = $data;

        return $this;
    }
}
