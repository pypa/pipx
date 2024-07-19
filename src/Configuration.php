<?php

namespace Cyberfusion\ClusterApi;

class Configuration
{
    private const URL_PRODUCTION = 'https://core-api.cyberfusion.io/api/v1/';

    private string $url = self::URL_PRODUCTION;
    private ?string $username = null;
    private ?string $password = null;
    private ?string $accessToken;

    public static function withCredentials(string $username, string $password): self
    {
        return (new self())
            ->setUsername($username)
            ->setPassword($password);
    }

    public static function withAccessToken(string $accessToken): self
    {
        return (new self())->setAccessToken($accessToken);
    }

    public function getUrl(): string
    {
        return $this->url;
    }

    public function setUrl(string $url): self
    {
        $this->url = $url;

        return $this;
    }

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): self
    {
        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): self
    {
        $this->password = $password;

        return $this;
    }

    public function hasCredentials(): bool
    {
        return !empty($this->username) && !empty($this->password);
    }

    public function getAccessToken(): ?string
    {
        return $this->accessToken;
    }

    public function hasAccessToken(): bool
    {
        return !empty($this->accessToken);
    }

    public function setAccessToken(?string $accessToken): self
    {
        $this->accessToken = $accessToken;

        return $this;
    }
}
