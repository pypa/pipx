<?php

namespace Vdhicts\Cyberfusion\ClusterApi;

class Request
{
    public const METHOD_GET = 'GET';
    public const METHOD_POST = 'POST';
    public const METHOD_PATCH = 'PATCH';
    public const METHOD_PUT = 'PUT';
    public const METHOD_DELETE = 'DELETE';

    private string $method;
    private string $url;
    private array $body;
    private bool $requiresAuthentication = true;

    /**
     * Request constructor.
     * @param string $method
     * @param string $url
     * @param array $body
     */
    public function __construct(string $method = self::METHOD_GET, string $url = '', array $body = [])
    {
        $this->method = $method;
        $this->url = $url;
        $this->body = $body;
    }

    public function getMethod(): string
    {
        return $this->method;
    }

    public function setMethod(string $method): Request
    {
        $availableMethods = [
            self::METHOD_GET,
            self::METHOD_POST,
            self::METHOD_PATCH,
            self::METHOD_PUT,
            self::METHOD_DELETE
        ];
        if (in_array($method, $availableMethods)) {
            $this->method = $method;
        }

        return $this;
    }

    public function getUrl(): string
    {
        return $this->url;
    }

    public function setUrl(string $url): Request
    {
        $this->url = $url;

        return $this;
    }

    public function getBody(): array
    {
        return $this->body;
    }

    public function setBody(array $body): Request
    {
        $this->body = $body;

        return $this;
    }

    public function authenticationRequired(): bool
    {
        return $this->requiresAuthentication;
    }

    public function setAuthenticationRequired(bool $requiresAuthentication): Request
    {
        $this->requiresAuthentication = $requiresAuthentication;

        return $this;
    }
}
