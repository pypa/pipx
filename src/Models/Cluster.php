<?php

namespace Cyberfusion\ClusterApi\Models;

use ArrayObject;
use Cyberfusion\ClusterApi\Enums\MeilisearchEnvironment;
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
    private ?array $httpRetryProperties = null;
    private ?bool $phpIoncubeEnabled = null;
    private ?string $kernelcareLicenseKey = null;
    private ?string $meilisearchMasterKey = null;
    private ?string $meilisearchEnvironment = null;
    private ?int $meilisearchBackupInterval = null;
    private ?int $meilisearchBackupLocalRetention = null;
    private ?string $newRelicApmLicenseKey = null;
    private ?string $newRelicMariadbPassword = null;
    private ?string $newRelicInfrastructureLicenseKey = null;
    private ?string $redisPassword = null;
    private ?int $redisMemoryLimit = null;
    private array $nodejsVersions = [];
    private ?string $nodeJsVersion = null;
    private ?int $customerId = null;
    private ?bool $wordpressToolkitEnabled = null;
    private ?bool $databaseToolkitEnabled = null;
    private ?int $mariaDbBackupInterval = null;
    private ?int $mariaDbBackupLocalRetention = null;
    private ?string $postgreSQLVersion = null;
    private ?int $postgreSQLBackupInterval = null;
    private ?int $posgreSQLBackupLocalRetention = null;
    private ?bool $malwareToolkitEnabled = null;
    private ?bool $malwareToolkitScansEnabled = null;
    private ?bool $bubblewrapToolkitEnabled = null;
    private ?bool $syncToolkitEnabled = null;
    private ?bool $automaticBorgRepositoriesPruneEnabled = null;
    private ?bool $phpSessionSpreadEnabled = null;
    private ?bool $automaticUpgradesEnabled = null;
    private ?bool $firewallRulesExternalProvidersEnabled = null;
    private ?string $description = null;
    private ?int $siteId = null;
    private ?int $id = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;
    private ?string $grafanaDomain = null;
    private ?string $singleStoreStudioDomain = null;
    private ?string $singleStoreApiDomain = null;
    private ?string $singleStoreLicenseKey = null;
    private ?string $singleStoreRootPassword = null;
    private ?string $elasticsearchDefaultUsersPassword = null;
    private ?string $rabbitMqErlangCookie = null;
    private ?string $rabbitMqAdminPassword = null;
    private ?string $metabaseDomain = null;
    private ?string $metabaseDatabasePassword = null;
    private ?string $kibanaDomain = null;
    private ?string $rabbitMqManagementDomain = null;

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

    public function getHttpRetryProperties(): ?array
    {
        return $this->httpRetryProperties;
    }

    public function setHttpRetryProperties(?array $httpRetryProperties): self
    {
        $this->httpRetryProperties = $httpRetryProperties;

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

    public function getNewRelicApmLicenseKey(): ?string
    {
        return $this->newRelicApmLicenseKey;
    }

    public function setNewRelicApmLicenseKey(?string $newRelicApmLicenseKey): self
    {
        Validator::value($newRelicApmLicenseKey)
            ->minLength(40)
            ->maxLength(40)
            ->pattern('^[a-zA-Z0-9]+$')
            ->validate();

        $this->newRelicApmLicenseKey = $newRelicApmLicenseKey;

        return $this;
    }

    public function getNewRelicMariadbPassword(): ?string
    {
        return $this->newRelicMariadbPassword;
    }

    public function setNewRelicMariadbPassword(?string $newRelicMariadbPassword): self
    {
        Validator::value($newRelicMariadbPassword)
            ->minLength(24)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->newRelicMariadbPassword = $newRelicMariadbPassword;

        return $this;
    }

    public function getNewRelicInfrastructureLicenseKey(): ?string
    {
        return $this->newRelicInfrastructureLicenseKey;
    }

    public function setNewRelicInfrastructureLicenseKey(?string $newRelicInfrastructureLicenseKey): self
    {
        Validator::value($newRelicInfrastructureLicenseKey)
            ->minLength(40)
            ->maxLength(40)
            ->pattern('^[a-zA-Z0-9]+$')
            ->validate();

        $this->newRelicInfrastructureLicenseKey = $newRelicInfrastructureLicenseKey;

        return $this;
    }

    public function getMeilisearchMasterKey(): ?string
    {
        return $this->meilisearchMasterKey;
    }

    public function setMeilisearchMasterKey(?string $meilisearchMasterKey): self
    {
        Validator::value($meilisearchMasterKey)
            ->minLength(16)
            ->maxLength(24)
            ->pattern('^[a-zA-Z0-9]+$')
            ->validate();

        $this->meilisearchMasterKey = $meilisearchMasterKey;

        return $this;
    }

    public function getMeilisearchEnvironment(): ?string
    {
        return $this->meilisearchEnvironment;
    }

    public function setMeilisearchEnvironment(?string $meilisearchEnvironment): self
    {
        Validator::value($meilisearchEnvironment)
            ->valueIn(MeilisearchEnvironment::AVAILABLE)
            ->validate();

        $this->meilisearchEnvironment = $meilisearchEnvironment;

        return $this;
    }

    public function getMeilisearchBackupInterval(): ?int
    {
        return $this->meilisearchBackupInterval;
    }

    public function setMeilisearchBackupInterval(?int $meilisearchBackupInterval): self
    {
        Validator::value($meilisearchBackupInterval)
            ->minAmount(1)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->meilisearchBackupInterval = $meilisearchBackupInterval;

        return $this;
    }

    public function getMeilisearchBackupLocalRetention(): ?int
    {
        return $this->meilisearchBackupLocalRetention;
    }

    public function setMeilisearchBackupLocalRetention(?int $meilisearchBackupLocalRetention): self
    {
        Validator::value($meilisearchBackupLocalRetention)
            ->minAmount(1)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->meilisearchBackupLocalRetention = $meilisearchBackupLocalRetention;
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
            ->minAmount(1)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->mariaDbBackupInterval = $mariaDbBackupInterval;
        return $this;
    }

    public function getMariaDbBackupLocalRetention(): ?int
    {
        return $this->mariaDbBackupLocalRetention;
    }

    public function setMariaDbBackupLocalRetention(?int $mariaDbBackupLocalRetention): self
    {
        Validator::value($mariaDbBackupLocalRetention)
            ->minAmount(1)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->mariaDbBackupLocalRetention = $mariaDbBackupLocalRetention;
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
            ->minAmount(1)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->postgreSQLBackupInterval = $postgreSQLBackupInterval;
        return $this;
    }

    public function getPosgreSQLBackupLocalRetention(): ?int
    {
        return $this->posgreSQLBackupLocalRetention;
    }

    public function setPosgreSQLBackupLocalRetention(?int $posgreSQLBackupLocalRetention): self
    {
        Validator::value($posgreSQLBackupLocalRetention)
            ->minAmount(1)
            ->maxAmount(24)
            ->nullable()
            ->validate();

        $this->posgreSQLBackupLocalRetention = $posgreSQLBackupLocalRetention;
        return $this;
    }

    public function isMalwareToolkitEnabled(): ?bool
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

    public function getAutomaticUpgradesEnabled(): ?bool
    {
        return $this->automaticUpgradesEnabled;
    }

    public function setAutomaticUpgradesEnabled(?bool $automaticUpgradesEnabled): self
    {
        $this->automaticUpgradesEnabled = $automaticUpgradesEnabled;

        return $this;
    }

    public function getFirewallRulesExternalProvidersEnabled(): ?bool
    {
        return $this->firewallRulesExternalProvidersEnabled;
    }

    public function setFirewallRulesExternalProvidersEnabled(?bool $firewallRulesExternalProvidersEnabled): self
    {
        $this->firewallRulesExternalProvidersEnabled = $firewallRulesExternalProvidersEnabled;
        return $this;
    }

    public function getSiteId(): ?int
    {
        return $this->siteId;
    }

    public function setSiteId(?int $siteId): self
    {
        $this->siteId = $siteId;
        return $this;
    }

    public function getDescription(): string
    {
        return $this->description;
    }

    public function setDescription(string $description): self
    {
        Validator::value($description)
            ->maxLength(255)
            ->pattern('^[a-zA-Z0-9-_. ]+$')
            ->validate();

        $this->description = $description;

        return $this;
    }

    public function getGrafanaDomain(): ?string
    {
        return $this->grafanaDomain;
    }

    public function setGrafanaDomain(?string $grafanaDomain): self
    {
        $this->grafanaDomain = $grafanaDomain;
        return $this;
    }

    public function getSingleStoreStudioDomain(): ?string
    {
        return $this->singleStoreStudioDomain;
    }

    public function setSingleStoreStudioDomain(?string $singleStoreStudioDomain): self
    {
        $this->singleStoreStudioDomain = $singleStoreStudioDomain;
        return $this;
    }

    public function getSingleStoreApiDomain(): ?string
    {
        return $this->singleStoreApiDomain;
    }

    public function setSingleStoreApiDomain(?string $singleStoreApiDomain): self
    {
        $this->singleStoreApiDomain = $singleStoreApiDomain;
        return $this;
    }

    public function getSingleStoreLicenseKey(): ?string
    {
        return $this->singleStoreLicenseKey;
    }

    public function setSingleStoreLicenseKey(?string $singleStoreLicenseKey): self
    {
        $this->singleStoreLicenseKey = $singleStoreLicenseKey;
        return $this;
    }

    public function getSingleStoreRootPassword(): ?string
    {
        return $this->singleStoreRootPassword;
    }

    public function setSingleStoreRootPassword(?string $singleStoreRootPassword): self
    {
        $this->singleStoreRootPassword = $singleStoreRootPassword;
        return $this;
    }

    public function getElasticsearchDefaultUsersPassword(): ?string
    {
        return $this->elasticsearchDefaultUsersPassword;
    }

    public function setElasticsearchDefaultUsersPassword(?string $elasticsearchDefaultUsersPassword): self
    {
        $this->elasticsearchDefaultUsersPassword = $elasticsearchDefaultUsersPassword;
        return $this;
    }

    public function getRabbitMqErlangCookie(): ?string
    {
        return $this->rabbitMqErlangCookie;
    }

    public function setRabbitMqErlangCookie(?string $rabbitMqErlangCookie): self
    {
        $this->rabbitMqErlangCookie = $rabbitMqErlangCookie;
        return $this;
    }

    public function getRabbitMqAdminPassword(): ?string
    {
        return $this->rabbitMqAdminPassword;
    }

    public function setRabbitMqAdminPassword(?string $rabbitMqAdminPassword): self
    {
        $this->rabbitMqAdminPassword = $rabbitMqAdminPassword;
        return $this;
    }

    public function getMetabaseDomain(): ?string
    {
        return $this->metabaseDomain;
    }

    public function setMetabaseDomain(?string $metabaseDomain): self
    {
        $this->metabaseDomain = $metabaseDomain;
        return $this;
    }

    public function getMetabaseDatabasePassword(): ?string
    {
        return $this->metabaseDatabasePassword;
    }

    public function setMetabaseDatabasePassword(?string $metabaseDatabasePassword): self
    {
        $this->metabaseDatabasePassword = $metabaseDatabasePassword;
        return $this;
    }

    public function getKibanaDomain(): ?string
    {
        return $this->kibanaDomain;
    }

    public function setKibanaDomain(?string $kibanaDomain): self
    {
        $this->kibanaDomain = $kibanaDomain;
        return $this;
    }

    public function getRabbitMqManagementDomain(): ?string
    {
        return $this->rabbitMqManagementDomain;
    }

    public function setRabbitMqManagementDomain(?string $rabbitMqManagementDomain): self
    {
        $this->rabbitMqManagementDomain = $rabbitMqManagementDomain;
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
            ->setCustomPhpModulesNames(Arr::get($data, 'custom_php_modules_names', []))
            ->setPhpSettings(Arr::get($data, 'php_settings', []))
            ->setHttpRetryProperties(Arr::get($data, 'http_retry_properties'))
            ->setPhpIoncubeEnabled(Arr::get($data, 'php_ioncube_enabled'))
            ->setKernelcareLicenseKey(Arr::get($data, 'kernelcare_license_key'))
            ->setNewRelicApmLicenseKey(Arr::get($data, 'new_relic_apm_license_key'))
            ->setNewRelicMariadbPassword(Arr::get($data, 'new_relic_mariadb_password'))
            ->setNewRelicInfrastructureLicenseKey(Arr::get($data, 'new_relic_infrastructure_license_key'))
            ->setMeilisearchMasterKey(Arr::get($data, 'meilisearch_master_key'))
            ->setMeilisearchEnvironment(Arr::get($data, 'meilisearch_environment'))
            ->setMeilisearchBackupInterval(Arr::get($data, 'meilisearch_backup_interval'))
            ->setMeilisearchBackupLocalRetention(Arr::get($data, 'meilisearch_backup_local_retention'))
            ->setRedisPassword(Arr::get($data, 'redis_password'))
            ->setRedisMemoryLimit(Arr::get($data, 'redis_memory_limit'))
            ->setNodejsVersions(Arr::get($data, 'nodejs_versions', []))
            ->setNodejsVersion(Arr::get($data, 'nodejs_version'))
            ->setCustomerId(Arr::get($data, 'customer_id'))
            ->setWordpressToolkitEnabled(Arr::get($data, 'wordpress_toolkit_enabled'))
            ->setDatabaseToolkitEnabled(Arr::get($data, 'database_toolkit_enabled'))
            ->setMariaDbBackupInterval(Arr::get($data, 'mariadb_backup_interval'))
            ->setMariaDbBackupLocalRetention(Arr::get($data, 'mariadb_backup_local_retention'))
            ->setPostgreSQLVersion(Arr::get($data, 'postgresql_version'))
            ->setPostgreSQLBackupInterval(Arr::get($data, 'postgresql_backup_interval'))
            ->setPosgreSQLBackupLocalRetention(Arr::get($data, 'postgresql_backup_local_retention'))
            ->setMalwareToolkitEnabled(Arr::get($data, 'malware_toolkit_enabled'))
            ->setMalwareToolkitScansEnabled(Arr::get($data, 'malware_toolkit_scans_enabled'))
            ->setBubblewrapToolkitEnabled(Arr::get($data, 'bubblewrap_toolkit_enabled'))
            ->setSyncToolkitEnabled(Arr::get($data, 'sync_toolkit_enabled'))
            ->setAutomaticBorgRepositoriesPruneEnabled(Arr::get($data, 'automatic_borg_repositories_prune_enabled'))
            ->setPhpSessionSpreadEnabled(Arr::get($data, 'php_sessions_spread_enabled'))
            ->setAutomaticUpgradesEnabled(Arr::get($data, 'automatic_upgrades_enabled'))
            ->setFirewallRulesExternalProvidersEnabled(Arr::get($data, 'firewall_rules_external_providers_enabled'))
            ->setSiteId(Arr::get($data, 'site_id'))
            ->setDescription(Arr::get($data, 'description'))
            ->setGrafanaDomain(Arr::get($data, 'grafana_domain'))
            ->setSingleStoreStudioDomain(Arr::get($data, 'single_store_studio_domain'))
            ->setSingleStoreApiDomain(Arr::get($data, 'single_store_api_domain'))
            ->setSingleStoreLicenseKey(Arr::get($data, 'single_store_license_key'))
            ->setSingleStoreRootPassword(Arr::get($data, 'single_store_root_password'))
            ->setElasticsearchDefaultUsersPassword(Arr::get($data, 'elastisearch_default_users_password'))
            ->setRabbitMqErlangCookie(Arr::get($data, 'rabbit_mq_erlang_cookie'))
            ->setRabbitMqAdminPassword(Arr::get($data, 'rabbit_mq_admin_password'))
            ->setMetabaseDomain(Arr::get($data, 'metabase_domain'))
            ->setMetabaseDatabasePassword(Arr::get($data, 'metabase_database_password'))
            ->setKibanaDomain(Arr::get($data, 'kibana_domain'))
            ->setRabbitMqManagementDomain(Arr::get($data, 'rabbit_mq_management_domain'))
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
            'php_settings' => new ArrayObject($this->getPhpSettings()),
            'http_retry_properties' => $this->getHttpRetryProperties()
                ? new ArrayObject($this->getHttpRetryProperties())
                : null,
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
            'mariadb_backup_local_retention' => $this->getMariaDbBackupLocalRetention(),
            'postgresql_version' => $this->getPostgreSQLVersion(),
            'postgresql_backup_interval' => $this->getPostgreSQLBackupInterval(),
            'postgresql_backup_local_retention' => $this->getPosgreSQLBackupLocalRetention(),
            'malware_toolkit_enabled' => $this->isMalwareToolkitEnabled(),
            'malware_toolkit_scans_enabled' => $this->isMalwareToolkitScansEnabled(),
            'bubblewrap_toolkit_enabled' => $this->isBubblewrapToolkitEnabled(),
            'sync_toolkit_enabled' => $this->isSyncToolkitEnabled(),
            'automatic_borg_repositories_prune_enabled' => $this->isAutomaticBorgRepositoriesPruneEnabled(),
            'php_sessions_spread_enabled' => $this->isPhpSessionSpreadEnabled(),
            'description' => $this->getDescription(),
            'new_relic_apm_license_key' => $this->getNewRelicApmLicenseKey(),
            'new_relic_infrastructure_license_key' => $this->getNewRelicInfrastructureLicenseKey(),
            'new_relic_mariadb_password' => $this->getNewRelicMariadbPassword(),
            'meilisearch_master_key' => $this->getMeilisearchMasterKey(),
            'meilisearch_environment' => $this->getMeilisearchEnvironment(),
            'meilisearch_backup_interval' => $this->getMeilisearchBackupInterval(),
            'meilisearch_backup_local_retention' => $this->getMeilisearchBackupLocalRetention(),
            'automatic_upgrades_enabled' => $this->getAutomaticUpgradesEnabled(),
            'firewall_rules_external_providers_enabled' => $this->getFirewallRulesExternalProvidersEnabled(),
            'site_id' => $this->getSiteId(),
            'grafana_domain' => $this->getGrafanaDomain(),
            'single_store_studio_domain' => $this->getSingleStoreStudioDomain(),
            'single_store_api_domain' => $this->getSingleStoreApiDomain(),
            'single_store_license_key' => $this->getSingleStoreLicenseKey(),
            'single_store_root_password' => $this->getSingleStoreRootPassword(),
            'elasticsearch_default_users_password' => $this->getElasticsearchDefaultUsersPassword(),
            'rabbit_mq_erlang_cookie' => $this->getRabbitMqErlangCookie(),
            'rabbit_mq_admin_password' => $this->getRabbitMqAdminPassword(),
            'metabase_domain' => $this->getMetabaseDomain(),
            'metabase_database_password' => $this->getMetabaseDatabasePassword(),
            'kibana_domain' => $this->getKibanaDomain(),
            'rabbit_mq_management_domain' => $this->getRabbitMqManagementDomain(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
