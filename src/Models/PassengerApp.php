<?php

namespace Cyberfusion\ClusterApi\Models;

use ArrayObject;
use Cyberfusion\ClusterApi\Enums\PassengerAppType;
use Cyberfusion\ClusterApi\Enums\PassengerEnvironment;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class PassengerApp extends ClusterModel
{
    private string $name;
    private int $unixUserId;
    private string $environment = PassengerEnvironment::PRODUCTION;
    private array $environmentVariables = [];
    private int $maxPoolSize;
    private int $maxRequests;
    private int $poolIdleTime;
    private int $port;
    private string $appType = PassengerAppType::NODEJS;
    private string $appRoot;
    private ?string $nodejsVersion;
    private ?string $startupFile;
    private bool $isNamespaced = false;
    private ?int $cpuLimit = null;
    private ?int $id = null;
    private ?int $clusterId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): self
    {
        Validator::value($name)
            ->maxLength(64)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getUnixUserId(): int
    {
        return $this->unixUserId;
    }

    public function setUnixUserId(int $unixUserId): self
    {
        $this->unixUserId = $unixUserId;

        return $this;
    }

    public function getEnvironment(): string
    {
        return $this->environment;
    }

    public function setEnvironment(string $environment): self
    {
        Validator::value($environment)
            ->valueIn(PassengerEnvironment::AVAILABLE)
            ->validate();

        $this->environment = $environment;

        return $this;
    }

    public function getEnvironmentVariables(): array
    {
        return $this->environmentVariables;
    }

    public function setEnvironmentVariables(array $environmentVariables): self
    {
        $this->environmentVariables = $environmentVariables;

        return $this;
    }

    public function getMaxPoolSize(): int
    {
        return $this->maxPoolSize;
    }

    public function setMaxPoolSize(int $maxPoolSize): self
    {
        $this->maxPoolSize = $maxPoolSize;

        return $this;
    }

    public function getMaxRequests(): int
    {
        return $this->maxRequests;
    }

    public function setMaxRequests(int $maxRequests): self
    {
        $this->maxRequests = $maxRequests;

        return $this;
    }

    public function getPoolIdleTime(): int
    {
        return $this->poolIdleTime;
    }

    public function setPoolIdleTime(int $poolIdleTime): self
    {
        $this->poolIdleTime = $poolIdleTime;

        return $this;
    }

    public function getPort(): int
    {
        return $this->port;
    }

    public function setPort(int $port): self
    {
        $this->port = $port;

        return $this;
    }

    public function getAppType(): string
    {
        return $this->appType;
    }

    public function setAppType(string $appType): self
    {
        Validator::value($appType)
            ->valueIn(PassengerAppType::AVAILABLE)
            ->validate();

        $this->appType = $appType;

        return $this;
    }

    public function getAppRoot(): string
    {
        return $this->appRoot;
    }

    public function setAppRoot(string $appRoot): self
    {
        Validator::value($appRoot)
            ->path()
            ->validate();

        $this->appRoot = $appRoot;

        return $this;
    }

    public function getNodejsVersion(): ?string
    {
        return $this->nodejsVersion;
    }

    public function setNodejsVersion(?string $nodejsVersion): self
    {
        Validator::value($nodejsVersion)
            ->nullable()
            ->pattern('^[0-9]{1,2}\.[0-9]{1,2}$')
            ->validate();

        $this->nodejsVersion = $nodejsVersion;

        return $this;
    }

    public function getStartupFile(): ?string
    {
        return $this->startupFile;
    }

    public function setStartupFile(?string $startupFile): self
    {
        Validator::value($startupFile)
            ->nullable()
            ->path()
            ->endsWith('.js')
            ->validate();

        $this->startupFile = $startupFile;

        return $this;
    }

    public function isNamespaced(): bool
    {
        return $this->isNamespaced;
    }

    public function setIsNamespaced(bool $isNamespaced): self
    {
        $this->isNamespaced = $isNamespaced;

        return $this;
    }

    public function getCpuLimit(): ?int
    {
        return $this->cpuLimit;
    }

    public function setCpuLimit(?int $cpuLimit): self
    {
        $this->cpuLimit = $cpuLimit;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): self
    {
        $this->id = $id;

        return $this;
    }

    public function getClusterId(): ?int
    {
        return $this->clusterId;
    }

    public function setClusterId(?int $clusterId): self
    {
        $this->clusterId = $clusterId;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): self
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): self
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setUnixUserId(Arr::get($data, 'unix_user_id'))
            ->setEnvironment(Arr::get($data, 'environment'))
            ->setEnvironmentVariables(Arr::get($data, 'environment_variables'))
            ->setMaxPoolSize(Arr::get($data, 'max_pool_size'))
            ->setMaxRequests(Arr::get($data, 'max_requests'))
            ->setPoolIdleTime(Arr::get($data, 'pool_idle_time'))
            ->setPort(Arr::get($data, 'port'))
            ->setAppType(Arr::get($data, 'app_type'))
            ->setNodejsVersion(Arr::get($data, 'nodejs_version'))
            ->setStartupFile(Arr::get($data, 'startup_file'))
            ->setIsNamespaced((bool)Arr::get($data, 'is_namespaced'))
            ->setCpuLimit(Arr::get($data, 'cpu_limit'))
            ->setAppRoot(Arr::get($data, 'app_root'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'unix_user_id' => $this->getUnixUserId(),
            'environment' => $this->getEnvironment(),
            'environment_variables' => new ArrayObject($this->getEnvironmentVariables()),
            'max_pool_size' => $this->getMaxPoolSize(),
            'max_requests' => $this->getMaxRequests(),
            'pool_idle_time' => $this->getPoolIdleTime(),
            'port' => $this->getPort(),
            'app_type' => $this->getAppType(),
            'nodejs_version' => $this->getNodejsVersion(),
            'startup_file' => $this->getStartupFile(),
            'is_namespaced' => $this->isNamespaced(),
            'cpu_limit' => $this->getCpuLimit(),
            'app_root' => $this->getAppRoot(),
            'id' => $this->getId(),
            'cluster_id' => $this->getClusterId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
