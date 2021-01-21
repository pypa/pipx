<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Login implements Model
{
    public ?string $grantType = null;
    public string $username;
    public string $password;
    public string $scope = '';
    public ?string $clientId = null;
    public ?string $clientSecret = null;

    public function toArray(): array
    {
        return [
            'grant_type' => $this->grantType,
            'username' => $this->username,
            'password' => $this->password,
            'scope' => $this->scope,
            'client_id' => $this->clientId,
            'client_secret' => $this->clientSecret,
        ];
    }
}
