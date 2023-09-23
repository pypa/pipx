<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class Cluster extends ClusterModel
{
    private string $name = '';
    private array $groups = [];
    private ?string $unixUsersHomeDirectory = null;
    private array $phpVersions = [];
    private ?string $mariaDbVersion = null;
    private ?string $mariaDbClusterName = null;
    private array $customPhpModulesNames = [];
    private array $phpSettings = [];
    private ?bool $phpIoncubeEnabled = null;
    private ?string $kernelcareLicenseKey = null;
    private ?string $redisPassword = null;
    private ?int $redisMemoryLimit = null;
    private array $nodejsVersions = [];
    private ?string $nodeJsVersion = null;
    private ?int $customerId = null;
    private ?bool $wordpressToolkitEnabled = null;
    private ?bool $databaseToolkitEnabled = null;
    private ?int $mariaDbBackupInterval = null;
    private ?string $postgreSQLVersion = null;
    private ?int $postgreSQLBackupInterval = null;
    private ?bool $malwareToolkitEnabled = null;
    private ?bool $malwareToolkitScansEnabled = null;
    private ?bool $bubblewrapToolkitEnabled = null;
    private ?bool $syncToolkitEnabled = null;
    private ?bool $automaticBorgRepositoriesPruneEnabled = null;
    private ?bool $phpSessionSpreadEnabled = null;
    private ?string $description = null;
    private ?int $id = null;
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
            ->pattern('^[a-z0-9-.]+$')
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getGroups(): ?array
    {
        return $this->groups;
    }

    public function setGroups(array $groups): self
    {
        $this->groups = $groups;

        return $this;
    }

    public function getUnixUsersHomeDirectory(): ?string
    {
        return $this->unixUsersHomeDirectory;
    }

    public function setUnixUsersHomeDirectory(?string $unixUsersHomeDirectory): self
    {
        Validator::value($unixUsersHomeDirectory)
            ->nullable()
            ->path()
            ->validate();

        $this->unixUsersHomeDirectory = $unixUsersHomeDirectory;

        return $this;
    }

    public function getPhpVersions(): array
    {
        return $this->phpVersions;
    }

    public function setPhpVersions(array $phpVersions): self
    {
        $this->phpVersions = $phpVersions;

        return $this;
    }

    public function getMariaDbVersion(): ?string
    {
        return $this->mariaDbVersion;
    }

    public function setMariaDbVersion(?string $mariaDbVersion): self
    {
        $this->mariaDbVersion = $mariaDbVersion;

        return $this;
    }

    public function getMariaDbClusterName(): ?string
    {
        return $this->mariaDbClusterName;
    }

    public function setMariaDbClusterName(?string $mariaDbClusterName): self
    {
        $this->mariaDbClusterName = $mariaDbClusterName;

        return $this;
    }

    public function getCustomPhpModulesNames(): array
    {
        return $this->customPhpModulesNames;
    }

    public function setCustomPhpModulesNames(array $customPhpModulesNames): self
    {
        $this->customPhpModulesNames = $customPhpModulesNames;

        return $this;
    }

    public function getPhpSettings(): array
    {
        return $this->phpSettings;
    }

    public function setPhpSettings(array $phpSettings): self
    {
        $this->phpSettings = $phpSettings;

        return $this;
    }

    public function isPhpIoncubeEnabled(): ?bool
    {
        return $this->phpIoncubeEnabled;
    }

    public function setPhpIoncubeEnabled(?bool $phpIoncubeEnabled): self
    {
        $this->phpIoncubeEnabled = $phpIoncubeEnabled;

        return $this;
    }

    public function getKernelcareLicenseKey(): ?string
    {
        return $this->kernelcareLicenseKey;
    }

    public function setKernelcareLicenseKey(?string $kernelcareLicenseKey): self
    {
        $this->kernelcareLicenseKey = $kernelcareLicenseKey;

        return $this;
    }

    public function getRedisPassword(): ?string
    {
        return $this->redisPassword;
    }

    public function setRedisPassword(?string $redisPassword): self
    {
        $this->redisPassword = $redisPassword;

        return $this;
    }

    public function getRedisMemoryLimit(): ?int
    {
        return $this->redisMemoryLimit;
    }

    public function setRedisMemoryLimit(?int $redisMemoryLimit): self
    {
        Validator::value($redisMemoryLimit)
            ->minAmount(0)
            ->nullable()
            ->validate();

        $this->redisMemoryLimit = $redisMemoryLimit;

        return $this;
    }

    public function getNodejsVersions(): array
    {
        return $this->nodejsVersions;
    }

    public function setNodejsVersions(array $nodejsVersions): self
    {
        Validator::value($nodejsVersions)
            ->each()
            ->pattern('^[0-9]{1,2}\.[0-9]{1,2}$')
            ->validate();

        $this->nodejsVersions = $nodejsVersions;

        return $this;
    }

    public function getNodeJsVersion(): ?string
    {
        return $this->nodeJsVersion;
    }

    public function setNodeJsVersion(?string $nodeJsVersion): self
    {
        $this->nodeJsVersion = $nodeJsVersion;

        return $this;
    }

    public function getCustomerId(): ?int
    {
        return $this->customerId;
    }

    public function setCustomerId(?int $customerId): self
    {
        Validator::value($customerId)
            ->nullable()
            ->minAmount(0)
            ->pattern('^[0-9]+$')
            ->validate();

        $this->customerId = $customerId;

        return $this;
    }

    public function isWordpressToolkitEnabled(): ?bool
    {
        return $this->wordpressToolkitEnabled;
    }

    public function setWordpressToolkitEnabled(?bool $wordpressToolkitEnabled): self
    {
        $this->wordpressToolkitEnabled = $wordpressToolkitEnabled;

        return $this;
    }

    public function isDatabaseToolkitEnabled(): ?bool
    {
        return $this->databaseToolkitEnabled;
    }

    public function setDatabaseToolkitEnabled(?bool $databaseToolkitEnabled): self
    {
        $this->databaseToolkitEnabled = $databaseToolkitEnabled;

        return $this;
    }

    public function getMariaDbBackupInterval(): ?int
    {
        return $this->mariaDbBackupInterval;
    }

    public function setMariaDbBackupInterval(?int $mariaDbBackupInterval): self
    {
        Validator::value($mariaDbBackupInterval)
            ->minAmount(4)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->mariaDbBackupInterval = $mariaDbBackupInterval;
        return $this;
    }

    public function getPostgreSQLVersion(): ?string
    {
        return $this->postgreSQLVersion;
    }

    public function setPostgreSQLVersion(?string $postgreSQLVersion): self
    {
        $this->postgreSQLVersion = $postgreSQLVersion;

        return $this;
    }

    public function getPostgreSQLBackupInterval(): ?int
    {
        return $this->postgreSQLBackupInterval;
    }

    public function setPostgreSQLBackupInterval(?int $postgreSQLBackupInterval): self
    {
        Validator::value($postgreSQLBackupInterval)
            ->minAmount(4)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->postgreSQLBackupInterval = $postgreSQLBackupInterval;
        return $this;
    }

    public function istMalwareToolkitEnabled(): ?bool
    {
        return $this->malwareToolkitEnabled;
    }

    public function setMalwareToolkitEnabled(?bool $malwareToolkitEnabled): self
    {
        $this->malwareToolkitEnabled = $malwareToolkitEnabled;

        return $this;
    }

    public function isMalwareToolkitScansEnabled(): ?bool
    {
        return $this->malwareToolkitScansEnabled;
    }

    public function setMalwareToolkitScansEnabled(?bool $malwareToolkitScansEnabled): self
    {
        $this->malwareToolkitScansEnabled = $malwareToolkitScansEnabled;

        return $this;
    }

    public function isBubblewrapToolkitEnabled(): ?bool
    {
        return $this->bubblewrapToolkitEnabled;
    }

    public function setBubblewrapToolkitEnabled(?bool $bubblewrapToolkitEnabled): self
    {
        $this->bubblewrapToolkitEnabled = $bubblewrapToolkitEnabled;

        return $this;
    }

    public function isSyncToolkitEnabled(): ?bool
    {
        return $this->syncToolkitEnabled;
    }

    public function setSyncToolkitEnabled(?bool $syncToolkitEnabled): self
    {
        $this->syncToolkitEnabled = $syncToolkitEnabled;

        return $this;
    }

    public function isAutomaticBorgRepositoriesPruneEnabled(): ?bool
    {
        return $this->automaticBorgRepositoriesPruneEnabled;
    }

    public function setAutomaticBorgRepositoriesPruneEnabled(?bool $automaticBorgRepositoriesPruneEnabled): self
    {
        $this->automaticBorgRepositoriesPruneEnabled = $automaticBorgRepositoriesPruneEnabled;

        return $this;
    }

    public function isPhpSessionSpreadEnabled(): ?bool
    {
        return $this->phpSessionSpreadEnabled;
    }

    public function setPhpSessionSpreadEnabled(?bool $phpSessionSpreadEnabled): self
    {
        $this->phpSessionSpreadEnabled = $phpSessionSpreadEnabled;

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
            ->maxLength(255)
            ->pattern('^[a-zA-Z0-9-_ ]+$')
            ->validate();

        $this->description = $description;

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
            ->setName(Arr::get($data, 'name', ''))
            ->setGroups(Arr::get($data, 'groups', []))
            ->setUnixUsersHomeDirectory(Arr::get($data, 'unix_users_home_directory'))
            ->setPhpVersions(Arr::get($data, 'php_versions', []))
            ->setMariaDbVersion(Arr::get($data, 'mariadb_version'))
            ->setMariaDbClusterName(Arr::get($data, 'mariadb_cluster_name'))
            ->setPhpSettings(Arr::get($data, 'php_settings', []))
            ->setCustomPhpModulesNames(Arr::get($data, 'custom_php_modules_names', []))
            ->setPhpIoncubeEnabled(Arr::get($data, 'php_ioncube_enabled'))
            ->setKernelcareLicenseKey(Arr::get($data, 'kernelcare_license_key'))
            ->setRedisPassword(Arr::get($data, 'redis_password'))
            ->setRedisMemoryLimit(Arr::get($data, 'redis_memory_limit'))
            ->setNodejsVersions(Arr::get($data, 'nodejs_versions', []))
            ->setNodejsVersion(Arr::get($data, 'nodejs_version'))
            ->setCustomerId(Arr::get($data, 'customer_id'))
            ->setWordpressToolkitEnabled(Arr::get($data, 'wordpress_toolkit_enabled'))
            ->setDatabaseToolkitEnabled(Arr::get($data, 'database_toolkit_enabled'))
            ->setMariaDbBackupInterval(Arr::get($data, 'mariadb_backup_interval'))
            ->setPostgreSQLVersion(Arr::get($data, 'postgresql_version'))
            ->setPostgreSQLBackupInterval(Arr::get($data, 'postgresql_backup_interval'))
            ->setMalwareToolkitEnabled(Arr::get($data, 'malware_toolkit_enabled'))
            ->setMalwareToolkitScansEnabled(Arr::get($data, 'malware_toolkit_scans_enabled'))
            ->setBubblewrapToolkitEnabled(Arr::get($data, 'bubblewrap_toolkit_enabled'))
            ->setSyncToolkitEnabled(Arr::get($data, 'sync_toolkit_enabled'))
            ->setAutomaticBorgRepositoriesPruneEnabled(Arr::get($data, 'automatic_borg_repositories_prune_enabled'))
            ->setPhpSessionSpreadEnabled(Arr::get($data, 'php_sessions_spread_enabled'))
            ->setDescription(Arr::get($data, 'description'))
            ->setId(Arr::get($data, 'id'))
            ->setCreatedAt(Arr::get($data, 'created_at'))
            ->setUpdatedAt(Arr::get($data, 'updated_at'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'groups' => $this->getGroups(),
            'unix_users_home_directory' => $this->getUnixUsersHomeDirectory(),
            'php_versions' => $this->getPhpVersions(),
            'mariadb_version' => $this->getMariaDbVersion(),
            'mariadb_cluster_name' => $this->getMariaDbClusterName(),
            'php_settings' => $this->getPhpSettings(),
            'custom_php_modules_names' => $this->getCustomPhpModulesNames(),
            'php_ioncube_enabled' => $this->isPhpIoncubeEnabled(),
            'kernelcare_license_key' => $this->getKernelcareLicenseKey(),
            'redis_password' => $this->getRedisPassword(),
            'redis_memory_limit' => $this->getRedisMemoryLimit(),
            'nodejs_versions' => $this->getNodejsVersions(),
            'nodejs_version' => $this->getNodejsVersion(),
            'customer_id' => $this->getCustomerId(),
            'wordpress_toolkit_enabled' => $this->isWordpressToolkitEnabled(),
            'database_toolkit_enabled' => $this->isDatabaseToolkitEnabled(),
            'mariadb_backup_interval' => $this->getMariaDbBackupInterval(),
            'postgresql_version' => $this->getPostgreSQLVersion(),
            'postgresql_backup_interval' => $this->getPostgreSQLBackupInterval(),
            'malware_toolkit_enabled' => $this->istMalwareToolkitEnabled(),
            'malware_toolkit_scans_enabled' => $this->isMalwareToolkitScansEnabled(),
            'bubblewrap_toolkit_enabled' => $this->isBubblewrapToolkitEnabled(),
            'sync_toolkit_enabled' => $this->isSyncToolkitEnabled(),
            'automatic_borg_repositories_prune_enabled' => $this->isAutomaticBorgRepositoriesPruneEnabled(),
            'php_sessions_spread_enabled' => $this->isPhpSessionSpreadEnabled(),
            'description' => $this->getDescription(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
