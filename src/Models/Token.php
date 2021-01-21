<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Token implements Model
{
    public string $accessToken;
    public string $tokenType;

    public function fromArray(array $data): Token
    {
        $login = new self();
        $login->accessToken = Arr::get($data, 'access_token', '');
        $login->tokenType = Arr::get($data, 'token_type', '');
        return $login;
    }

    public function toArray(): array
    {
        return [
            'access_token' => $this->accessToken,
            'token_type' => $this->tokenType,
        ];
    }
}
