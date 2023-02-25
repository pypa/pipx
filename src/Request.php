<?php

namespace Cyberfusion\ClusterApi;

class Request
{
    public const METHOD_GET = 'GET';
    public const METHOD_POST = 'POST';
    public const METHOD_PATCH = 'PATCH';
    public const METHOD_PUT = 'PUT';
    public const METHOD_DELETE = 'DELETE';

    public const BODY_SCHEMA_JSON = 'json';
    public const BODY_SCHEMA_FORM = 'form';

    private string $bodySchema = self::BODY_SCHEMA_JSON;
    private bool $requiresAuthentication = true;

    public function __construct(
        private string $method = self::METHOD_GET,
        private string $url = '',
        private array $body = []
    ) {
    }

    public function getMethod(): string
    {
        return $this->method;
    }

    public function setMethod(string $method): self
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

    public function setUrl(string $url): self
    {
        $this->url = $url;

        return $this;
    }

    public function getBody(): array
    {
        return $this->body;
    }

    public function setBody(array $body): self
    {
        $this->body = $body;

        return $this;
    }

    public function authenticationRequired(): bool
    {
        return $this->requiresAuthentication;
    }

    public function setAuthenticationRequired(bool $requiresAuthentication): self
    {
        $this->requiresAuthentication = $requiresAuthentication;

        return $this;
    }

    public function getBodySchema(): string
    {
        return $this->bodySchema;
    }

    public function setBodySchema(string $bodySchema): self
    {
        if (!in_array($bodySchema, [self::BODY_SCHEMA_JSON, self::BODY_SCHEMA_FORM])) {
            $bodySchema = self::BODY_SCHEMA_JSON;
        }

        $this->bodySchema = $bodySchema;

        return $this;
    }
}
