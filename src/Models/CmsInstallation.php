<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Support\Validator;

class CmsInstallation extends ClusterModel implements Model
{
    private string $databaseName;
    private string $databaseUserName;
    private string $databaseUserPassword;
    private string $databaseHost;
    private string $siteTitle;
    private string $siteUrl;
    private string $locale;
    private string $version;
    private string $adminUsername;
    private string $adminPassword;
    private string $adminEmailAddress;

    public function getDatabaseName(): string
    {
        return $this->databaseName;
    }

    public function setDatabaseName(string $databaseName): CmsInstallation
    {
        Validator::value($databaseName)
            ->maxLength(63)
            ->pattern('^[a-zA-Z0-9-_]+$')
            ->validate();

        $this->databaseName = $databaseName;

        return $this;
    }

    public function getDatabaseUserName(): string
    {
        return $this->databaseUserName;
    }

    public function setDatabaseUserName(string $databaseUserName): CmsInstallation
    {
        Validator::value($databaseUserName)
            ->maxLength(63)
            ->pattern('^[a-zA-Z0-9-_]+$')
            ->validate();

        $this->databaseUserName = $databaseUserName;

        return $this;
    }

    public function getDatabaseUserPassword(): string
    {
        return $this->databaseUserPassword;
    }

    public function setDatabaseUserPassword(string $databaseUserPassword): CmsInstallation
    {
        Validator::value($databaseUserPassword)
            ->minLength(1)
            ->validate();

        $this->databaseUserPassword = $databaseUserPassword;

        return $this;
    }

    public function getDatabaseHost(): string
    {
        return $this->databaseHost;
    }

    public function setDatabaseHost(string $databaseHost): CmsInstallation
    {
        Validator::value($databaseHost)
            ->ip()
            ->validate();

        $this->databaseHost = $databaseHost;

        return $this;
    }

    public function getSiteTitle(): string
    {
        return $this->siteTitle;
    }

    public function setSiteTitle(string $siteTitle): CmsInstallation
    {
        Validator::value($siteTitle)
            ->maxLength(253)
            ->pattern('^[a-zA-Z0-9-_ ]+$')
            ->validate();

        $this->siteTitle = $siteTitle;

        return $this;
    }

    public function getSiteUrl(): string
    {
        return $this->siteUrl;
    }

    public function setSiteUrl(string $siteUrl): CmsInstallation
    {
        Validator::value($siteUrl)
            ->maxLength(2083)
            ->validate();

        $this->siteUrl = $siteUrl;

        return $this;
    }

    public function getLocale(): string
    {
        return $this->locale;
    }

    public function setLocale(string $locale): CmsInstallation
    {
        Validator::value($locale)
            ->maxLength(15)
            ->pattern('^[a-zA-Z_]+$')
            ->validate();

        $this->locale = $locale;

        return $this;
    }

    public function getVersion(): string
    {
        return $this->version;
    }

    public function setVersion(string $version): CmsInstallation
    {
        Validator::value($version)
            ->maxLength(6)
            ->pattern('^[0-9.]+$')
            ->validate();

        $this->version = $version;

        return $this;
    }

    public function getAdminUsername(): string
    {
        return $this->adminUsername;
    }

    public function setAdminUsername(string $adminUsername): CmsInstallation
    {
        Validator::value($adminUsername)
            ->maxLength(60)
            ->pattern('^[a-zA-Z0-9-_]+$')
            ->validate();

        $this->adminUsername = $adminUsername;

        return $this;
    }

    public function getAdminPassword(): string
    {
        return $this->adminPassword;
    }

    public function setAdminPassword(string $adminPassword): CmsInstallation
    {
        Validator::value($adminPassword)
            ->minLength(1)
            ->validate();

        $this->adminPassword = $adminPassword;

        return $this;
    }

    public function getAdminEmailAddress(): string
    {
        return $this->adminEmailAddress;
    }

    public function setAdminEmailAddress(string $adminEmailAddress): CmsInstallation
    {
        Validator::value($adminEmailAddress)
            ->email()
            ->validate();

        $this->adminEmailAddress = $adminEmailAddress;

        return $this;
    }

    public function fromArray(array $data): CmsInstallation
    {
        return $this
            ->setDatabaseName(Arr::get($data, 'database_name'))
            ->setDatabaseUserName(Arr::get($data, 'database_user_name'))
            ->setDatabaseUserPassword(Arr::get($data, 'database_user_password'))
            ->setDatabaseHost(Arr::get($data, 'database_host'))
            ->setSiteTitle(Arr::get($data, 'site_title'))
            ->setSiteUrl(Arr::get($data, 'site_url'))
            ->setLocale(Arr::get($data, 'locale'))
            ->setVersion(Arr::get($data, 'version'))
            ->setAdminUsername(Arr::get($data, 'admin_username'))
            ->setAdminPassword(Arr::get($data, 'admin_password'))
            ->setAdminEmailAddress(Arr::get($data, 'admin_email_address'));
    }

    public function toArray(): array
    {
        return [
            'database_name' => $this->getDatabaseName(),
            'database_user_name' => $this->getDatabaseUserName(),
            'database_user_password' => $this->getDatabaseUserPassword(),
            'database_host' => $this->getDatabaseHost(),
            'site_title' => $this->getSiteTitle(),
            'site_url' => $this->getSiteUrl(),
            'locale' => $this->getLocale(),
            'version' => $this->getVersion(),
            'admin_username' => $this->getAdminUsername(),
            'admin_password' => $this->getAdminPassword(),
            'admin_email_address' => $this->getAdminEmailAddress(),
        ];
    }
}
