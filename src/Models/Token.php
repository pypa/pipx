<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Enums\TokenType;
use Cyberfusion\ClusterApi\Support\Validator;

class Token extends ClusterModel implements Model
{
    private string $accessToken;
    private string $tokenType;
    private int $expiresIn;

    public function getAccessToken(): string
    {
        return $this->accessToken;
    }

    public function setAccessToken(string $accessToken): Token
    {
        Validator::value($accessToken)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->accessToken = $accessToken;

        return $this;
    }

    public function getExpiresIn(): int
    {
        return $this->expiresIn;
    }

    public function setExpiresIn(int $expiresIn): Token
    {
        $this->expiresIn = $expiresIn;

        return $this;
    }

    public function getTokenType(): string
    {
        return $this->tokenType;
    }

    public function setTokenType(string $tokenType): Token
    {
        Validator::value($tokenType)
            ->valueIn(TokenType::AVAILABLE)
            ->validate();

        $this->tokenType = $tokenType;

        return $this;
    }

    public function fromArray(array $data): Token
    {
        return $this
            ->setAccessToken(Arr::get($data, 'access_token', ''))
            ->setExpiresIn(Arr::get($data, 'expires_in', ''))
            ->setTokenType(Arr::get($data, 'token_type', ''));
    }

    public function toArray(): array
    {
        return [
            'access_token' => $this->getAccessToken(),
            'expires_in' => $this->getExpiresIn(),
            'token_type' => $this->getTokenType(),
        ];
    }
}
