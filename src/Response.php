<?php

namespace Vdhicts\Cyberfusion\ClusterApi;

class Response
{
    private int $statusCode;
    private string $statusMessage;
    private array $data;

    /**
     * Response constructor.
     * @param int $statusCode
     * @param string $statusMessage
     * @param array $data
     */
    public function __construct(int $statusCode, string $statusMessage, array $data = [])
    {
        $this->statusCode = $statusCode;
        $this->statusMessage = $statusMessage;
        $this->data = $data;
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

    /**
     * @param string|null $attribute
     * @return mixed
     */
    public function getData(string $attribute = null)
    {
        if (is_null($attribute)) {
            return $this->data;
        }

        if (! array_key_exists($attribute, $this->data)) {
            return null;
        }

        return $this->data[$attribute];
    }

    public function setData(array $data): Response
    {
        $this->data = $data;

        return $this;
    }
}
