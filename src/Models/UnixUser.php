<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Enums\ShellPath;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class UnixUser extends ClusterModel implements Model
{
    private string $username;
    private string $password;
    private ?string $homeDirectory = null;
    private ?string $sshDirectory = null;
    private ?string $description = null;
    private ?string $defaultPhpVersion = null;
    private ?string $defaultNodejsVersion = null;
    private ?string $virtualHostsDirectory = null;
    private ?string $mailDomainsDirectory = null;
    private ?string $borgRepositoriesDirectory = null;
    private string $shellPath = ShellPath::BASH;
    private bool $recordUsageFiles = false;
    private bool $asyncSupportEnabled = false;
    private ?string $rabbitMqUsername = null;
    private ?string $rabbitMqVirtualHostName = null;
    private ?string $rabbitMqPassword = null;
    private ?string $rabbitMqEncryptionKey = null;
    private int $clusterId;
    private ?int $id = null;
    private ?int $unixId = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getUsername(): string
    {
        return $this->username;
    }

    public function setUsername(string $username): self
    {
        Validator::value($username)
            ->maxLength(32)
            ->pattern('^[a-z0-9-_]+$')
            ->validate();

        $this->username = $username;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): self
    {
        Validator::value($password)
            ->minLength(24)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->password = $password;

        return $this;
    }

    public function getDescription(): ?string
    {
        return $this->description;
    }

    public function setDescription(?string $description): self
    {
        Validator::value($description)
            ->nullable()
            ->pattern('^[a-zA-Z0-9-_ ]+$')
            ->maxLength(255)
            ->validate();

        $this->description = $description;

        return $this;
    }

    public function getDefaultPhpVersion(): ?string
    {
        return $this->defaultPhpVersion;
    }

    public function setDefaultPhpVersion(?string $defaultPhpVersion): self
    {
        $this->defaultPhpVersion = $defaultPhpVersion;

        return $this;
    }

    public function getDefaultNodejsVersion(): ?string
    {
        return $this->defaultNodejsVersion;
    }

    public function setDefaultNodejsVersion(?string $defaultNodejsVersion): self
    {
        Validator::value($defaultNodejsVersion)
            ->nullable()
            ->pattern('^[0-9]{1,2}\.[0-9]{1,2}$')
            ->validate();

        $this->defaultNodejsVersion = $defaultNodejsVersion;

        return $this;
    }

    public function getHomeDirectory(): ?string
    {
        return $this->homeDirectory;
    }

    public function setHomeDirectory(?string $homeDirectory): self
    {
        Validator::value($homeDirectory)
            ->nullable()
            ->path()
            ->validate();

        $this->homeDirectory = $homeDirectory;

        return $this;
    }

    public function getSshDirectory(): ?string
    {
        return $this->sshDirectory;
    }

    public function setSshDirectory(?string $sshDirectory): self
    {
        Validator::value($sshDirectory)
            ->nullable()
            ->path()
            ->validate();

        $this->sshDirectory = $sshDirectory;

        return $this;
    }

    public function getVirtualHostsDirectory(): ?string
    {
        return $this->virtualHostsDirectory;
    }

    public function setVirtualHostsDirectory(?string $virtualHostsDirectory): self
    {
        Validator::value($virtualHostsDirectory)
            ->nullable()
            ->path()
            ->validate();

        $this->virtualHostsDirectory = $virtualHostsDirectory;

        return $this;
    }

    public function getMailDomainsDirectory(): ?string
    {
        return $this->mailDomainsDirectory;
    }

    public function setMailDomainsDirectory(?string $mailDomainsDirectory): self
    {
        Validator::value($mailDomainsDirectory)
            ->nullable()
            ->path()
            ->validate();

        $this->mailDomainsDirectory = $mailDomainsDirectory;

        return $this;
    }

    public function getBorgRepositoriesDirectory(): ?string
    {
        return $this->borgRepositoriesDirectory;
    }

    public function setBorgRepositoriesDirectory(?string $borgRepositoriesDirectory): self
    {
        Validator::value($borgRepositoriesDirectory)
            ->nullable()
            ->path()
            ->validate();

        $this->borgRepositoriesDirectory = $borgRepositoriesDirectory;

        return $this;
    }

    public function getShellPath(): string
    {
        return $this->shellPath;
    }

    public function setShellPath(string $shellPath): self
    {
        Validator::value($shellPath)
            ->valueIn(ShellPath::AVAILABLE)
            ->validate();

        $this->shellPath = $shellPath;

        return $this;
    }

    public function getRecordUsageFiles(): bool
    {
        return $this->recordUsageFiles;
    }

    public function setRecordUsageFiles(bool $recordUsageFiles): self
    {
        $this->recordUsageFiles = $recordUsageFiles;

        return $this;
    }

    public function isAsyncSupportEnabled(): bool
    {
        return $this->asyncSupportEnabled;
    }

    public function setAsyncSupportEnabled(bool $asyncSupportEnabled): self
    {
        $this->asyncSupportEnabled = $asyncSupportEnabled;

        return $this;
    }

    public function getRabbitMqUsername(): ?string
    {
        return $this->rabbitMqUsername;
    }

    public function setRabbitMqUsername(?string $rabbitMqUsername): self
    {
        Validator::value($rabbitMqUsername)
            ->nullable()
            ->maxLength(32)
            ->pattern('^[a-z0-9-.]+$')
            ->validate();

        $this->rabbitMqUsername = $rabbitMqUsername;

        return $this;
    }

    public function getRabbitMqVirtualHostName(): ?string
    {
        return $this->rabbitMqVirtualHostName;
    }

    public function setRabbitMqVirtualHostName(?string $rabbitMqVirtualHostName): self
    {
        Validator::value($rabbitMqVirtualHostName)
            ->nullable()
            ->maxLength(32)
            ->pattern('^[a-z0-9-.]+$')
            ->validate();

        $this->rabbitMqVirtualHostName = $rabbitMqVirtualHostName;

        return $this;
    }

    public function getRabbitMqPassword(): ?string
    {
        return $this->rabbitMqPassword;
    }

    public function setRabbitMqPassword(?string $rabbitMqPassword): self
    {
        Validator::value($rabbitMqPassword)
            ->nullable()
            ->maxLength(255)
            ->pattern('^[a-zA-Z0-9]+$')
            ->validate();

        $this->rabbitMqPassword = $rabbitMqPassword;

        return $this;
    }

    public function getRabbitMqEncryptionKey(): ?string
    {
        return $this->rabbitMqEncryptionKey;
    }

    public function setRabbitMqEncryptionKey(?string $rabbitMqEncryptionKey): self
    {
        Validator::value($rabbitMqEncryptionKey)
            ->nullable()
            ->maxLength(255)
            ->pattern('^[a-z\=\_\-A-Z0-9]+$')
            ->validate();

        $this->rabbitMqEncryptionKey = $rabbitMqEncryptionKey;

        return $this;
    }

    public function getClusterId(): int
    {
        return $this->clusterId;
    }

    public function setClusterId(int $clusterId): self
    {
        $this->clusterId = $clusterId;

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

    public function getUnixId(): ?int
    {
        return $this->unixId;
    }

    public function setUnixId(?int $unixId): self
    {
        $this->unixId = $unixId;

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
            ->setUsername(Arr::get($data, 'username'))
            ->setPassword(Arr::get($data, 'password'))
            ->setHomeDirectory(Arr::get($data, 'home_directory'))
            ->setSshDirectory(Arr::get($data, 'ssh_directory'))
            ->setDescription(Arr::get($data, 'description'))
            ->setDefaultPhpVersion(Arr::get($data, 'default_php_version'))
            ->setDefaultNodejsVersion(Arr::get($data, 'default_nodejs_version'))
            ->setVirtualHostsDirectory(Arr::get($data, 'virtual_hosts_directory'))
            ->setMailDomainsDirectory(Arr::get($data, 'mail_domains_directory'))
            ->setBorgRepositoriesDirectory(Arr::get($data, 'borg_repositories_directory'))
            ->setShellPath(Arr::get($data, 'shell_path', ShellPath::BASH))
            ->setRecordUsageFiles(Arr::get($data, 'record_usage_files', false))
            ->setAsyncSupportEnabled(Arr::get($data, 'async_support_enabled', false))
            ->setRabbitMqUsername(Arr::get($data, 'rabbitmq_username'))
            ->setRabbitMqVirtualHostName(Arr::get($data, 'rabbitmq_virtual_host_name'))
            ->setRabbitMqPassword(Arr::get($data, 'rabbitmq_password'))
            ->setRabbitMqEncryptionKey(Arr::get($data, 'rabbitmq_encryption_key'))
            ->setUnixId(Arr::get($data, 'unix_id'))
            ->setId(Arr::get($data, 'id'))
            ->setClusterId(Arr::get($data, 'cluster_id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'username' => $this->getUsername(),
            'password' => $this->getPassword(),
            'home_directory' => $this->getHomeDirectory(),
            'ssh_directory' => $this->getSshDirectory(),
            'description' => $this->getDescription(),
            'default_php_version' => $this->getDefaultPhpVersion(),
            'default_nodejs_version' => $this->getDefaultNodejsVersion(),
            'virtual_hosts_directory' => $this->getVirtualHostsDirectory(),
            'mail_domains_directory' => $this->getMailDomainsDirectory(),
            'borg_repositories_directory' => $this->getBorgRepositoriesDirectory(),
            'shell_path' => $this->getShellPath(),
            'record_usage_files' => $this->getRecordUsageFiles(),
            'async_support_enabled' => $this->isAsyncSupportEnabled(),
            'rabbitmq_username' => $this->getRabbitMqUsername(),
            'rabbitmq_virtual_host_name' => $this->getRabbitMqVirtualHostName(),
            'rabbitmq_password' => $this->getRabbitMqPassword(),
            'rabbitmq_encryption_key' => $this->getRabbitMqEncryptionKey(),
            'cluster_id' => $this->getClusterId(),
            'id' => $this->getId(),
            'unix_id' => $this->getUnixId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
