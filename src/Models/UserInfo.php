<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class UserInfo implements Model
{
    public string $username;
    public bool $isActive;
    public bool $isProvisioningUser;
    public bool $isSuperUser;
    public array $clusters = [];

    public function fromArray(array $data): UserInfo
    {
        $userInfo = new self();
        $userInfo->username = Arr::get($data, 'username');
        $userInfo->isActive = Arr::get($data, 'is_active');
        $userInfo->isProvisioningUser = Arr::get($data, 'is_provisioning_user');
        $userInfo->isSuperUser = Arr::get($data, 'is_superuser');
        $userInfo->clusters = Arr::get($data, 'clusters', []);
        return $userInfo;
    }

    public function toArray(): array
    {
        return [
            'username' => $this->username,
            'is_active' => $this->isActive,
            'is_provisioning_user' => $this->isProvisioningUser,
            'is_superuser' => $this->isSuperUser,
            'clusters' => $this->clusters,
        ];
    }
}
