<?php

namespace Vdhicts\Cyberfusion\ClusterApi;

class Configuration
{
    private const URL_LIVE = 'https://cluster-api.cyberfusion.nl/api/v1/';
    private const URL_SANDBOX = 'https://test-cluster-api.cyberfusion.nl/api/v1/';

    private string $url = self::URL_LIVE;
    private string $username;
    private string $password;
    private ?string $accessToken;
    private bool $sandbox = false;

    public static function withCredentials(string $username, string $password, bool $sandbox = false): Configuration
    {
        return (new self())
            ->setUsername($username)
            ->setPassword($password)
            ->setSandbox($sandbox);
    }

    public static function withAccessToken(string $accessToken): Configuration
    {
        return (new self())->setAccessToken($accessToken);
    }

    public function getUrl(): string
    {
        return $this->url;
    }

    public function setUrl(string $url): Configuration
    {
        $this->url = $url;

        return $this;
    }

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): Configuration
    {
        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): Configuration
    {
        $this->password = $password;

        return $this;
    }

    public function hasCredentials(): bool
    {
        return ! empty($this->username) && ! empty($this->password);
    }

    public function getAccessToken(): ?string
    {
        return $this->accessToken;
    }

    public function hasAccessToken(): bool
    {
        return ! empty($this->accessToken);
    }

    public function setAccessToken(?string $accessToken): Configuration
    {
        $this->accessToken = $accessToken;

        return $this;
    }

    /**
     * @return bool
     */
    public function isSandbox(): bool
    {
        return $this->sandbox;
    }

    /**
     * @param bool $sandbox
     * @return Configuration
     */
    public function setSandbox(bool $sandbox): Configuration
    {
        $this->sandbox = $sandbox;

        $this->url = $sandbox
            ? self::URL_SANDBOX
            : self::URL_LIVE;

        return $this;
    }
}
