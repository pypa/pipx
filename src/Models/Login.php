<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Login extends ClusterModel implements Model
{
    private ?string $grantType = null;
    private string $username;
    private string $password;
    private string $scope = '';
    private ?string $clientId = null;
    private ?string $clientSecret = null;

    public function getGrantType(): ?string
    {
        return $this->grantType;
    }

    public function setGrantType(?string $grantType): Login
    {
        $this->grantType = $grantType;

        return $this;
    }

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): Login
    {
        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): Login
    {
        $this->password = $password;

        return $this;
    }

    public function getScope(): string
    {
        return $this->scope;
    }

    public function setScope(string $scope): Login
    {
        $this->scope = $scope;

        return $this;
    }

    public function getClientId(): ?string
    {
        return $this->clientId;
    }

    public function setClientId(?string $clientId): Login
    {
        $this->clientId = $clientId;

        return $this;
    }

    public function getClientSecret(): ?string
    {
        return $this->clientSecret;
    }

    public function setClientSecret(?string $clientSecret): Login
    {
        $this->clientSecret = $clientSecret;

        return $this;
    }

    public function toArray(): array
    {
        return [
            'grant_type' => $this->getGrantType(),
            'username' => $this->getUsername(),
            'password' => $this->getPassword(),
            'scope' => $this->getScope(),
            'client_id' => $this->getClientId(),
            'client_secret' => $this->getClientSecret(),
        ];
    }
}
