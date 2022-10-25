<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;

class ErrorLog extends ClusterModel implements Model
{
    private string $remoteAddress;
    private string $rawMessage;
    private string $method;
    private string $uri;
    private string $timestamp;
    private string $errorMessage;

    public function getRemoteAddress(): string
    {
        return $this->remoteAddress;
    }

    public function setRemoteAddress(string $remoteAddress): ErrorLog
    {
        $this->remoteAddress = $remoteAddress;

        return $this;
    }

    public function getRawMessage(): string
    {
        return $this->rawMessage;
    }

    public function setRawMessage(string $rawMessage): ErrorLog
    {
        Validator::value($rawMessage)
            ->maxLength(65535)
            ->pattern('^[ -~\n]+$')
            ->validate();

        $this->rawMessage = $rawMessage;

        return $this;
    }

    public function getMethod(): string
    {
        return $this->method;
    }

    public function setMethod(string $method): ErrorLog
    {
        $this->method = $method;

        return $this;
    }

    public function getUri(): string
    {
        return $this->uri;
    }

    public function setUri(string $uri): ErrorLog
    {
        $this->uri = $uri;

        return $this;
    }

    public function getTimestamp(): string
    {
        return $this->timestamp;
    }

    public function setTimestamp(string $timestamp): ErrorLog
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function getErrorMessage(): string
    {
        return $this->errorMessage;
    }

    public function setErrorMessage(string $errorMessage): ErrorLog
    {
        Validator::value($errorMessage)
            ->maxLength(65535)
            ->pattern('^[ -~\n]+$')
            ->validate();

        $this->errorMessage = $errorMessage;

        return $this;
    }

    public function fromArray(array $data): ErrorLog
    {
        return $this
            ->setRemoteAddress(Arr::get($data, 'remote_address'))
            ->setRawMessage(Arr::get($data, 'raw_message'))
            ->setMethod(Arr::get($data, 'method'))
            ->setUri(Arr::get($data, 'uri'))
            ->setTimestamp(Arr::get($data, 'timestamp'))
            ->setErrorMessage(Arr::get($data, 'error_message'));
    }

    public function toArray(): array
    {
        return [
            'remote_address' => $this->getRemoteAddress(),
            'raw_message' => $this->getRawMessage(),
            'method' => $this->getMethod(),
            'uri' => $this->getUri(),
            'timestamp' => $this->getTimestamp(),
            'error_message' => $this->getErrorMessage(),
        ];
    }
}
