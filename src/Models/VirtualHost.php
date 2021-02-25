<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class VirtualHost implements Model
{
    public string $domain;
    public array $serverAliases = [];
    public int $unixUserId;
    public string $documentRoot;
    public string $publicRoot;
    public ?int $fpmPoolId = null;
    public bool $forceSsl = true;
    public ?string $customConfig = null;
    public ?string $balancerBackendName = null;
    public array $deployCommands = [];
    public ?int $id = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): VirtualHost
    {
        $virtualHost = new self();
        $virtualHost->domain = Arr::get($data, 'domain');
        $virtualHost->serverAliases = Arr::get($data, 'server_aliases', []);
        $virtualHost->unixUserId = Arr::get($data, 'unix_user_id');
        $virtualHost->documentRoot = Arr::get($data, 'document_root');
        $virtualHost->publicRoot = Arr::get($data, 'public_root');
        $virtualHost->fpmPoolId = Arr::get($data, 'fpm_pool_id');
        $virtualHost->forceSsl = Arr::get($data, 'force_ssl');
        $virtualHost->balancerBackendName = Arr::get($data, 'balancer_backend_name');
        $virtualHost->customConfig = Arr::get($data, 'custom_config');
        $virtualHost->deployCommands = Arr::get($data, 'deploy_commands', []);
        $virtualHost->id = Arr::get($data, 'id');
        $virtualHost->clusterId = Arr::get($data, 'cluster_id');
        $virtualHost->createdAt = Arr::get($data, 'created_at');
        $virtualHost->updatedAt = Arr::get($data, 'updated_at');
        return $virtualHost;
    }

    public function toArray(): array
    {
        return [
            'domain' => $this->domain,
            'server_aliases' => $this->serverAliases,
            'unix_user_id' => $this->unixUserId,
            'document_root' => $this->documentRoot,
            'public_root' => $this->publicRoot,
            'fpm_pool_id' => $this->fpmPoolId,
            'force_ssl' => $this->forceSsl,
            'custom_config' => $this->customConfig,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'balancer_backend_name' => $this->balancerBackendName,
            'deploy_commands' => $this->deployCommands,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
