<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Cluster extends ClusterModel implements Model
{
    private string $name = '';
    private array $groups = [];
    private ?string $unixUsersHomeDirectory = null;
    private ?string $databasesDataDirectory = null;
    private array $phpVersions = [];
    private array $customPhpModulesNames = [];
    private ?bool $phpIoncubeEnabled = null;
    private array $nodejsVersions = [];
    private ?string $customerId = null;
    private ?bool $wordpressToolkitEnabled = null;
    private ?bool $databaseToolkitEnabled = null;
    private ?bool $malwareToolkitEnabled = null;
    private ?bool $malwareToolkitScansEnabled = null;
    private ?bool $bubblewrapToolkitEnabled = null;
    private ?int $id = null;
    private ?string $createdAt = null;
    private ?string $updatedAt = null;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): Cluster
    {
        $this->name = $name;

        return $this;
    }

    public function getGroups(): ?array
    {
        return $this->groups;
    }

    public function setGroups(array $groups): Cluster
    {
        $this->groups = $groups;

        return $this;
    }

    public function getUnixUsersHomeDirectory(): ?string
    {
        return $this->unixUsersHomeDirectory;
    }

    public function setUnixUsersHomeDirectory(?string $unixUsersHomeDirectory): Cluster
    {
        $this->unixUsersHomeDirectory = $unixUsersHomeDirectory;

        return $this;
    }

    public function getDatabasesDataDirectory(): ?string
    {
        return $this->databasesDataDirectory;
    }

    public function setDatabasesDataDirectory(?string $databasesDataDirectory): Cluster
    {
        $this->databasesDataDirectory = $databasesDataDirectory;

        return $this;
    }

    public function getPhpVersions(): array
    {
        return $this->phpVersions;
    }

    public function setPhpVersions(array $phpVersions): Cluster
    {
        $this->phpVersions = $phpVersions;

        return $this;
    }

    public function getCustomPhpModulesNames(): array
    {
        return $this->customPhpModulesNames;
    }

    public function setCustomPhpModulesNames(array $customPhpModulesNames): Cluster
    {
        $this->customPhpModulesNames = $customPhpModulesNames;

        return $this;
    }

    public function isPhpIoncubeEnabled(): ?bool
    {
        return $this->phpIoncubeEnabled;
    }

    public function setPhpIoncubeEnabled(?bool $phpIoncubeEnabled): Cluster
    {
        $this->phpIoncubeEnabled = $phpIoncubeEnabled;

        return $this;
    }

    public function getNodejsVersions(): array
    {
        return $this->nodejsVersions;
    }

    public function setNodejsVersions(array $nodejsVersions): Cluster
    {
        $this->nodejsVersions = $nodejsVersions;

        return $this;
    }

    public function getCustomerId(): ?string
    {
        return $this->customerId;
    }

    public function setCustomerId(?string $customerId): Cluster
    {
        $this->customerId = $customerId;

        return $this;
    }

    public function isWordpressToolkitEnabled(): ?bool
    {
        return $this->wordpressToolkitEnabled;
    }

    public function setWordpressToolkitEnabled(?bool $wordpressToolkitEnabled): Cluster
    {
        $this->wordpressToolkitEnabled = $wordpressToolkitEnabled;

        return $this;
    }

    public function isDatabaseToolkitEnabled(): ?bool
    {
        return $this->databaseToolkitEnabled;
    }

    public function setDatabaseToolkitEnabled(?bool $databaseToolkitEnabled): Cluster
    {
        $this->databaseToolkitEnabled = $databaseToolkitEnabled;

        return $this;
    }

    public function istMalwareToolkitEnabled(): ?bool
    {
        return $this->malwareToolkitEnabled;
    }

    public function setMalwareToolkitEnabled(?bool $malwareToolkitEnabled): Cluster
    {
        $this->malwareToolkitEnabled = $malwareToolkitEnabled;

        return $this;
    }

    public function isMalwareToolkitScansEnabled(): ?bool
    {
        return $this->malwareToolkitScansEnabled;
    }

    public function setMalwareToolkitScansEnabled(?bool $malwareToolkitScansEnabled): Cluster
    {
        $this->malwareToolkitScansEnabled = $malwareToolkitScansEnabled;

        return $this;
    }

    public function isBubblewrapToolkitEnabled(): ?bool
    {
        return $this->bubblewrapToolkitEnabled;
    }

    public function setBubblewrapToolkitEnabled(?bool $bubblewrapToolkitEnabled): Cluster
    {
        $this->bubblewrapToolkitEnabled = $bubblewrapToolkitEnabled;

        return $this;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): Cluster
    {
        $this->id = $id;

        return $this;
    }

    public function getCreatedAt(): ?string
    {
        return $this->createdAt;
    }

    public function setCreatedAt(?string $createdAt): Cluster
    {
        $this->createdAt = $createdAt;

        return $this;
    }

    public function getUpdatedAt(): ?string
    {
        return $this->updatedAt;
    }

    public function setUpdatedAt(?string $updatedAt): Cluster
    {
        $this->updatedAt = $updatedAt;

        return $this;
    }

    public function fromArray(array $data): Cluster
    {
        return $this
            ->setName(Arr::get($data, 'name', ''))
            ->setGroups(Arr::get($data, 'groups', []))
            ->setUnixUsersHomeDirectory(Arr::get($data, 'unix_users_home_directory'))
            ->setDatabasesDataDirectory(Arr::get($data, 'databases_data_directory'))
            ->setPhpVersions(Arr::get($data, 'php_versions', []))
            ->setCustomPhpModulesNames(Arr::get($data, 'custom_php_modules_names', []))
            ->setPhpIoncubeEnabled(Arr::get($data, 'php_ioncube_enabled'))
            ->setNodejsVersions(Arr::get($data, 'nodejs_versions', []))
            ->setCustomerId(Arr::get($data, 'customer_id'))
            ->setWordpressToolkitEnabled(Arr::get($data, 'wordpress_toolkit_enabled'))
            ->setDatabaseToolkitEnabled(Arr::get($data, 'database_toolkit_enabled'))
            ->setMalwareToolkitEnabled(Arr::get($data, 'malware_toolkit_enabled'))
            ->setMalwareToolkitScansEnabled(Arr::get($data, 'malware_toolkit_scans_enabled'))
            ->setBubblewrapToolkitEnabled(Arr::get($data, 'bubblewrap_toolkit_enabled'))
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
            'databases_data_directory' => $this->getDatabasesDataDirectory(),
            'php_versions' => $this->getPhpVersions(),
            'custom_php_modules_names' => $this->getCustomPhpModulesNames(),
            'php_ioncube_enabled' => $this->isPhpIoncubeEnabled(),
            'nodejs_versions' => $this->getNodejsVersions(),
            'customer_id' => $this->getCustomerId(),
            'wordpress_toolkit_enabled' => $this->isWordpressToolkitEnabled(),
            'database_toolkit_enabled' => $this->isDatabaseToolkitEnabled(),
            'malware_toolkit_enabled' => $this->istMalwareToolkitEnabled(),
            'malware_toolkit_scans_enabled' => $this->isMalwareToolkitScansEnabled(),
            'bubblewrap_toolkit_enabled ' => $this->isBubblewrapToolkitEnabled(),
            'id' => $this->getId(),
            'created_at' => $this->getCreatedAt(),
            'updated_at' => $this->getUpdatedAt(),
        ];
    }
}
