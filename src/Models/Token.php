<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Token extends ClusterModel implements Model
{
    private string $accessToken;
    private string $tokenType;

    public function getAccessToken(): string
    {
        return $this->accessToken;
    }

    public function setAccessToken(string $accessToken): Token
    {
        $this->accessToken = $accessToken;

        return $this;
    }

    public function getTokenType(): string
    {
        return $this->tokenType;
    }

    public function setTokenType(string $tokenType): Token
    {
        $this->tokenType = $tokenType;

        return $this;
    }

    public function fromArray(array $data): Token
    {
        return $this
            ->setAccessToken(Arr::get($data, 'access_token', ''))
            ->setTokenType(Arr::get($data, 'token_type', ''));
    }

    public function toArray(): array
    {
        return [
            'access_token' => $this->getAccessToken(),
            'token_type' => $this->getTokenType(),
        ];
    }
}
