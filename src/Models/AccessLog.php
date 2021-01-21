<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class AccessLog implements Model
{
    public string $remoteAddress;
    public string $rawMessage;
    public string $method;
    public string $uri;
    public string $timestamp;
    public int $statusCode;
    public int $bytesSent;

    public function fromArray(array $data): AccessLog
    {
        $accessLog = new self();
        $accessLog->remoteAddress = Arr::get($data, 'remote_address');
        $accessLog->rawMessage = Arr::get($data, 'raw_message');
        $accessLog->method = Arr::get($data, 'method');
        $accessLog->uri = Arr::get($data, 'uri');
        $accessLog->timestamp = Arr::get($data, 'timestamp');
        $accessLog->statusCode = Arr::get($data, 'status_code');
        $accessLog->bytesSent = Arr::get($data, 'bytes_sent');
        return $accessLog;
    }

    public function toArray(): array
    {
        return [
            'remote_address' => $this->remoteAddress,
            'raw_message' => $this->rawMessage,
            'method' => $this->method,
            'uri' => $this->uri,
            'timestamp' => $this->timestamp,
            'status_code' => $this->statusCode,
            'bytes_sent' => $this->bytesSent,
        ];
    }
}
