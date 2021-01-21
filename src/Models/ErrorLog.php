<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class ErrorLog implements Model
{
    public string $remoteAddress;
    public string $rawMessage;
    public string $method;
    public string $uri;
    public string $timestamp;
    public string $errorMessage;

    public function fromArray(array $data): ErrorLog
    {
        $errorLog = new self();
        $errorLog->remoteAddress = Arr::get($data, 'remote_address');
        $errorLog->rawMessage = Arr::get($data, 'raw_message');
        $errorLog->method = Arr::get($data, 'method');
        $errorLog->uri = Arr::get($data, 'uri');
        $errorLog->timestamp = Arr::get($data, 'timestamp');
        $errorLog->errorMessage = Arr::get($data, 'error_message');
        return $errorLog;
    }

    public function toArray(): array
    {
        return [
            'remote_address' => $this->remoteAddress,
            'raw_message' => $this->rawMessage,
            'method' => $this->method,
            'uri' => $this->uri,
            'timestamp' => $this->timestamp,
            'error_message' => $this->errorMessage,
        ];
    }
}
