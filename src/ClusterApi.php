<?php

namespace Cyberfusion\ClusterApi;

use Cyberfusion\ClusterApi\Contracts\Client as ClientContract;
use Cyberfusion\ClusterApi\Endpoints\ApiUsers;
use Cyberfusion\ClusterApi\Endpoints\Authentication;
use Cyberfusion\ClusterApi\Endpoints\BasicAuthenticationRealms;
use Cyberfusion\ClusterApi\Endpoints\BorgArchives;
use Cyberfusion\ClusterApi\Endpoints\BorgRepositories;
use Cyberfusion\ClusterApi\Endpoints\CertificateManagers;
use Cyberfusion\ClusterApi\Endpoints\Certificates;
use Cyberfusion\ClusterApi\Endpoints\Clusters;
use Cyberfusion\ClusterApi\Endpoints\Cmses;
use Cyberfusion\ClusterApi\Endpoints\Crons;
use Cyberfusion\ClusterApi\Endpoints\CustomConfigs;
use Cyberfusion\ClusterApi\Endpoints\CustomConfigSnippets;
use Cyberfusion\ClusterApi\Endpoints\Customers;
use Cyberfusion\ClusterApi\Endpoints\Daemons;
use Cyberfusion\ClusterApi\Endpoints\Databases;
use Cyberfusion\ClusterApi\Endpoints\DatabaseUserGrants;
use Cyberfusion\ClusterApi\Endpoints\DatabaseUsers;
use Cyberfusion\ClusterApi\Endpoints\DomainRouters;
use Cyberfusion\ClusterApi\Endpoints\FirewallGroups;
use Cyberfusion\ClusterApi\Endpoints\FirewallRules;
use Cyberfusion\ClusterApi\Endpoints\FpmPools;
use Cyberfusion\ClusterApi\Endpoints\FtpUsers;
use Cyberfusion\ClusterApi\Endpoints\HAProxyListens;
use Cyberfusion\ClusterApi\Endpoints\HAProxyListensToNodes;
use Cyberfusion\ClusterApi\Endpoints\Health;
use Cyberfusion\ClusterApi\Endpoints\HostsEntries;
use Cyberfusion\ClusterApi\Endpoints\HtpasswdFiles;
use Cyberfusion\ClusterApi\Endpoints\HtpasswdUsers;
use Cyberfusion\ClusterApi\Endpoints\Logs;
use Cyberfusion\ClusterApi\Endpoints\MailAccounts;
use Cyberfusion\ClusterApi\Endpoints\MailAliases;
use Cyberfusion\ClusterApi\Endpoints\MailDomains;
use Cyberfusion\ClusterApi\Endpoints\MailHostnames;
use Cyberfusion\ClusterApi\Endpoints\Malwares;
use Cyberfusion\ClusterApi\Endpoints\MariaDbEncryptionKeys;
use Cyberfusion\ClusterApi\Endpoints\NodeAddons;
use Cyberfusion\ClusterApi\Endpoints\Nodes;
use Cyberfusion\ClusterApi\Endpoints\PassengerApps;
use Cyberfusion\ClusterApi\Endpoints\RedisInstances;
use Cyberfusion\ClusterApi\Endpoints\RootSshKeys;
use Cyberfusion\ClusterApi\Endpoints\SecurityTxtPolicies;
use Cyberfusion\ClusterApi\Endpoints\Sites;
use Cyberfusion\ClusterApi\Endpoints\SshKeys;
use Cyberfusion\ClusterApi\Endpoints\TaskCollections;
use Cyberfusion\ClusterApi\Endpoints\Tombstones;
use Cyberfusion\ClusterApi\Endpoints\UnixUsers;
use Cyberfusion\ClusterApi\Endpoints\UrlRedirects;
use Cyberfusion\ClusterApi\Endpoints\VirtualHosts;

class ClusterApi
{
    public function __construct(private ClientContract $client)
    {
    }

    public function apiUsers(): ApiUsers
    {
        return new ApiUsers($this->client);
    }

    public function authentication(): Authentication
    {
        return new Authentication($this->client);
    }

    public function basicAuthenticationRealms(): BasicAuthenticationRealms
    {
        return new BasicAuthenticationRealms($this->client);
    }

    public function borgArchives(): BorgArchives
    {
        return new BorgArchives($this->client);
    }

    public function borgRepositories(): BorgRepositories
    {
        return new BorgRepositories($this->client);
    }

    public function certificates(): Certificates
    {
        return new Certificates($this->client);
    }

    public function certificateManagers(): CertificateManagers
    {
        return new CertificateManagers($this->client);
    }

    public function clusters(): Clusters
    {
        return new Clusters($this->client);
    }

    public function cmses(): Cmses
    {
        return new Cmses($this->client);
    }

    public function crons(): Crons
    {
        return new Crons($this->client);
    }

    public function customers(): Customers
    {
        return new Customers($this->client);
    }

    public function customConfigs(): CustomConfigs
    {
        return new CustomConfigs($this->client);
    }

    public function customConfigSnippets(): CustomConfigSnippets
    {
        return new CustomConfigSnippets($this->client);
    }

    public function databases(): Databases
    {
        return new Databases($this->client);
    }

    public function databaseUsers(): DatabaseUsers
    {
        return new DatabaseUsers($this->client);
    }

    public function databaseUserGrants(): DatabaseUserGrants
    {
        return new DatabaseUserGrants($this->client);
    }

    public function domainRouters(): DomainRouters
    {
        return new DomainRouters($this->client);
    }

    public function firewallGroups(): FirewallGroups
    {
        return new FirewallGroups($this->client);
    }

    public function firewallRules(): FirewallRules
    {
        return new FirewallRules($this->client);
    }

    public function fpmPools(): FpmPools
    {
        return new FpmPools($this->client);
    }

    public function ftpUsers(): FtpUsers
    {
        return new FtpUsers($this->client);
    }

    public function haProxyListens(): HAProxyListens
    {
        return new HAProxyListens($this->client);
    }

    public function haProxyListensToNodes(): HAProxyListensToNodes
    {
        return new HAProxyListensToNodes($this->client);
    }

    public function health(): Health
    {
        return new Health($this->client);
    }

    public function hostsEntries(): HostsEntries
    {
        return new HostsEntries($this->client);
    }

    public function htpasswdFiles(): HtpasswdFiles
    {
        return new HtpasswdFiles($this->client);
    }

    public function htpasswdUsers(): HtpasswdUsers
    {
        return new HtpasswdUsers($this->client);
    }

    public function logs(): Logs
    {
        return new Logs($this->client);
    }

    public function mailAccounts(): MailAccounts
    {
        return new MailAccounts($this->client);
    }

    public function mailAliases(): MailAliases
    {
        return new MailAliases($this->client);
    }

    public function mailDomains(): MailDomains
    {
        return new MailDomains($this->client);
    }

    public function mailHostnames(): MailHostnames
    {
        return new MailHostnames($this->client);
    }

    public function malwares(): Malwares
    {
        return new Malwares($this->client);
    }

    public function mariaDbEncryptionKeys(): MariaDbEncryptionKeys
    {
        return new MariaDbEncryptionKeys($this->client);
    }

    public function nodes(): Nodes
    {
        return new Nodes($this->client);
    }

    public function nodeAddons(): NodeAddons
    {
        return new NodeAddons($this->client);
    }

    public function passengerApps(): PassengerApps
    {
        return new PassengerApps($this->client);
    }

    public function redisInstances(): RedisInstances
    {
        return new RedisInstances($this->client);
    }

    public function rootSshKeys(): RootSshKeys
    {
        return new RootSshKeys($this->client);
    }

    public function securityTxtPolicies(): SecurityTxtPolicies
    {
        return new SecurityTxtPolicies($this->client);
    }

    public function sites(): Sites
    {
        return new Sites($this->client);
    }

    public function sshKeys(): SshKeys
    {
        return new SshKeys($this->client);
    }

    public function taskCollections(): TaskCollections
    {
        return new TaskCollections($this->client);
    }

    public function tombstones(): Tombstones
    {
        return new Tombstones($this->client);
    }

    public function unixUsers(): UnixUsers
    {
        return new UnixUsers($this->client);
    }

    public function urlRedirects(): UrlRedirects
    {
        return new UrlRedirects($this->client);
    }

    public function virtualHosts(): VirtualHosts
    {
        return new VirtualHosts($this->client);
    }

    public function daemons(): Daemons
    {
        return new Daemons($this->client);
    }
}
