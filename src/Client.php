<?php

namespace Vdhicts\Cyberfusion\ClusterApi;

use GuzzleHttp\Client as GuzzleClient;
use Psr\Http\Message\ResponseInterface;
use Throwable;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Client as ClientContract;
use Vdhicts\Cyberfusion\ClusterApi\Endpoints\Clusters;
use Vdhicts\Cyberfusion\ClusterApi\Endpoints\Health;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ClientException;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ClusterApiException;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\DetailMessage;
use Vdhicts\Cyberfusion\ClusterApi\Models\HttpValidationError;
use Vdhicts\Cyberfusion\ClusterApi\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Support\Deployment;

class Client implements ClientContract
{
    private const CONNECT_TIMEOUT = 60;
    private const TIMEOUT = 180;

    private Configuration $configuration;
    private GuzzleClient $httpClient;
    private array $affectedClusters;

    /**
     * Client constructor.
     * @param Configuration $configuration
     * @param bool $manuallyAuthenticate
     * @throws ClientException
     * @throws ClusterApiException
     */
    public function __construct(Configuration $configuration, bool $manuallyAuthenticate = false)
    {
        $this->configuration = $configuration;

        // Initialize the HTTP client
        $this->initHttpClient();

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
    private function initHttpClient(): void
    {
        $baseUri = $this
            ->configuration
            ->getUrl();

        $this->httpClient = new GuzzleClient([
            'base_uri' => $baseUri,
            'timeout' => self::TIMEOUT,
            'connect_timeout' => self::CONNECT_TIMEOUT,
            'http_errors' => false,
        ]);
    }

    /**
     * Determines if the API is up.
     *
     * @return bool
     */
    private function isUp(): bool
    {
        // Retrieve the health status
        $healthEndpoint = new Health($this);
        try {
            $response = $healthEndpoint->get();
        } catch (RequestException $exception) {
            return false;
        }

        // Store and return if the API is up
        return $response
            ->getData('health')
            ->isUp();
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
            if (is_null($accessToken)) {
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
     * @return bool
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
     * @return string|null
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
     *
     * @param string $accessToken
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
     *
     * @param Request $request
     * @return array
     */
    private function getRequestOptions(Request $request): array
    {
        $requestOptions = [];
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
     *
     * @param ResponseInterface $response
     * @return array
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

    /**
     * @inheritDoc
     */
    public function addAffectedCluster(int $clusterId): Client
    {
        if (!in_array($clusterId, $this->affectedClusters)) {
            $this->affectedClusters[] = $clusterId;
        }

        return $this;
    }

    /**
     * @inheritDoc
     */
    public function deploy(): array
    {
        $affectedClusters = array_unique($this->affectedClusters);
        if (count($affectedClusters) === 0) {
            return [];
        }

        $clusterCommitResults = [];

        $clustersEndpoint = new Clusters($this);
        foreach ($this->affectedClusters as $affectedCluster) {
            $deployment = (new Deployment())->setClusterId($affectedCluster);

            try {
                $result = $clustersEndpoint->commit($affectedCluster);

                $deployment->setSuccess($result->isSuccess());
                $result->isSuccess()
                    ? $deployment->setCluster($result->getData('cluster'))
                    : $deployment->setError($result->getData('error'));
            } catch (RequestException $exception) {
                $deployment->setSuccess(false);
                $deployment->setError($exception->getMessage());
            }

            $clusterCommitResults[] = $deployment;

            $this->affectedClusters = Arr::exceptValue($this->affectedClusters, $affectedCluster);
        }

        return $clusterCommitResults;
    }

    public function __destruct()
    {
        if (!$this->configuration->autoDeploy()) {
            return;
        }

        $this->deploy();
    }
}
