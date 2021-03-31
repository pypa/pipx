<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class AccessLog extends ClusterModel implements Model
{
    private string $remoteAddress;
    private string $rawMessage;
    private string $method;
    private string $uri;
    private string $timestamp;
    private int $statusCode;
    private int $bytesSent;

    public function getRemoteAddress(): string
    {
        return $this->remoteAddress;
    }

    public function setRemoteAddress(string $remoteAddress): AccessLog
    {
        $this->remoteAddress = $remoteAddress;

        return $this;
    }

    public function getRawMessage(): string
    {
        return $this->rawMessage;
    }

    public function setRawMessage(string $rawMessage): AccessLog
    {
        $this->rawMessage = $rawMessage;

        return $this;
    }

    public function getMethod(): string
    {
        return $this->method;
    }

    public function setMethod(string $method): AccessLog
    {
        $this->method = $method;

        return $this;
    }

    public function getUri(): string
    {
        return $this->uri;
    }

    public function setUri(string $uri): AccessLog
    {
        $this->uri = $uri;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): AccessLog
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function getStatusCode(): int
    {
        return $this->statusCode;
    }

    public function setStatusCode(int $statusCode): AccessLog
    {
        $this->statusCode = $statusCode;

        return $this;
    }

    public function getBytesSent(): int
    {
        return $this->bytesSent;
    }

    public function setBytesSent(int $bytesSent): AccessLog
    {
        $this->bytesSent = $bytesSent;

        return $this;
    }

    public function fromArray(array $data): AccessLog
    {
        return $this
            ->setRemoteAddress(Arr::get($data, 'remote_address'))
            ->setRawMessage(Arr::get($data, 'raw_message'))
            ->setMethod(Arr::get($data, 'method'))
            ->setUri(Arr::get($data, 'uri'))
            ->setTimestamp(Arr::get($data, 'timestamp'))
            ->setStatusCode(Arr::get($data, 'status_code'))
            ->setBytesSent(Arr::get($data, 'bytes_sent'));
    }

    public function toArray(): array
    {
        return [
            'remote_address' => $this->getRemoteAddress(),
            'raw_message' => $this->getRawMessage(),
            'method' => $this->getMethod(),
            'uri' => $this->getUri(),
            'timestamp' => $this->getTimestamp(),
            'status_code' => $this->getStatusCode(),
            'bytes_sent' => $this->getBytesSent(),
        ];
    }
}
