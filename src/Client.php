<?php

namespace Cyberfusion\ClusterApi;

use Cyberfusion\ClusterApi\Contracts\Client as ClientContract;
use Cyberfusion\ClusterApi\Endpoints\Health;
use Cyberfusion\ClusterApi\Exceptions\ClientException;
use Cyberfusion\ClusterApi\Exceptions\ClusterApiException;
use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\DetailMessage;
use Cyberfusion\ClusterApi\Models\HttpValidationError;
use GuzzleHttp\Client as GuzzleClient;
use GuzzleHttp\ClientInterface;
use Psr\Http\Message\ResponseInterface;
use Throwable;

class Client implements ClientContract
{
    private const CONNECT_TIMEOUT = 60;

    private const TIMEOUT = 180;

    private const VERSION = '1.114.1';

    private const USER_AGENT = 'cyberfusion-cluster-api-client/' . self::VERSION;

    private ClientInterface $httpClient;

    /**
     * @throws ClientException
     * @throws ClusterApiException
     */
    public function __construct(
        private Configuration $configuration,
        bool $manuallyAuthenticate = false,
        ClientInterface $httpClient = null
    ) {
        // Initialize the HTTP client
        $this->initHttpClient($httpClient);

        // Check if the API is available
        if (!$this->isUp()) {
            throw ClientException::apiNotUp();
        }

        // Start authentication unless the authentication is done manually
        if (!$manuallyAuthenticate) {
            $this->authenticate();
        }
    }

    /**
     * Initialize the HTTP client with default configuration which is used for every request.
     */
    private function initHttpClient(ClientInterface $httpClient = null): void
    {
        if ($httpClient instanceof ClientInterface) {
            $this->httpClient = $httpClient;

            return;
        }

        $this->httpClient = new GuzzleClient([
            'timeout' => self::TIMEOUT,
            'connect_timeout' => self::CONNECT_TIMEOUT,
            'headers' => [
                'User-Agent' => self::USER_AGENT,
            ]
        ]);
    }

    /**
     * Determines if the API is up.
     */
    private function isUp(): bool
    {
        // Retrieve the health status
        $healthEndpoint = new Health($this);
        try {
            $response = $healthEndpoint->get();
        } catch (RequestException) {
            return false;
        }

        // Store and return if the API is up
        return (bool) $response
            ->getData('health')
            ?->isUp();
    }

    /**
     * @throws ClientException
     * @throws RequestException
     */
    private function authenticate(): void
    {
        // An access token or credentials are required
        if (!$this->configuration->hasAccessToken() && !$this->configuration->hasCredentials()) {
            throw ClientException::authenticationMissing();
        }

        // The access token is provided, so check if the token is valid
        if ($this->configuration->hasAccessToken()) {
            $accessTokenValid = $this->validateAccessToken();
            if ($accessTokenValid) {
                return;
            }
        }

        // The access token isn't provided or valid, so check if the username/password can be used
        if ($this->configuration->hasCredentials()) {
            $accessToken = $this->retrieveAccessToken();
            if ($accessToken === null) {
                throw ClientException::invalidCredentials();
            }

            $this->storeAccessToken($accessToken);

            return;
        }

        // No or invalid access token is provided and no or invalid credentials are provided
        throw ClientException::authenticationFailed();
    }

    /**
     * Determine if the current access token is valid.
     *
     * @throws RequestException
     */
    private function validateAccessToken(): bool
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('login/test-token');

        $response = $this->request($request);
        if (!$response->isSuccess()) {
            return false;
        }

        return $response->getData('is_active');
    }

    /**
     * Retrieve the access token with the credentials. Returns null when no access token could be retrieved.
     *
     * @throws RequestException
     */
    private function retrieveAccessToken(): ?string
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('login/access-token')
            ->setBody([
                'username' => $this->configuration->getUsername(),
                'password' => $this->configuration->getPassword(),
            ])
            ->setAuthenticationRequired(false)
            ->setBodySchema(Request::BODY_SCHEMA_FORM);

        $response = $this->request($request);
        if (!$response->isSuccess()) {
            return null;
        }

        return $response->getData('access_token');
    }

    /**
     * Store the access token in the configuration.
     */
    private function storeAccessToken(string $accessToken): void
    {
        $this
            ->configuration
            ->setAccessToken($accessToken);
    }

    /**
     * @inheritDoc
     */
    public function request(Request $request): Response
    {
        if ($request->authenticationRequired() && !$this->configuration->hasAccessToken()) {
            throw RequestException::authenticationRequired();
        }

        try {
            $response = $this
                ->httpClient
                ->request($request->getMethod(), $request->getUrl(), $this->getRequestOptions($request));
        } catch (Throwable $exception) {
            throw RequestException::requestFailed($exception->getMessage());
        }

        return new Response($response->getStatusCode(), $response->getReasonPhrase(), $this->parseBody($response));
    }

    /**
     * Determine the request options based on the request and configuration.
     */
    private function getRequestOptions(Request $request): array
    {
        $requestOptions = [
            // Never throw exceptions on 4xx and 5xx responses to ensure package behaviour
            'http_errors' => false,

            // Always use the base uri from the configuration
            'base_uri' => $this
                ->configuration
                ->getUrl(),
        ];
        if ($request->getBodySchema() === Request::BODY_SCHEMA_JSON) {
            $requestOptions['json'] = $request->getBody();
        } else {
            $requestOptions['form_params'] = $request->getBody();
        }
        if ($request->authenticationRequired()) {
            $requestOptions['headers'] = [
                'Authorization' => sprintf('Bearer %s', $this->configuration->getAccessToken()),
            ];
        }

        return $requestOptions;
    }

    /**
     * Parse the body to error models when applicable.
     */
    private function parseBody(ResponseInterface $response): array
    {
        $body = json_decode((string)$response->getBody(), true);
        if ($response->getStatusCode() < 300) {
            return $body;
        }

        if ($response->getStatusCode() === 422) { // Validation error
            return [
                'error' => (new HttpValidationError())->fromArray($body),
            ];
        }

        if ($response->getStatusCode() === 500) { // Internal server error
            return [
                'error' => (new DetailMessage())->fromArray(['detail' => $response->getReasonPhrase()]),
            ];
        }

        return [
            'error' => (new DetailMessage())->fromArray($body),
        ];
    }
}
