<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class UnixUser implements Model
{
    public string $username;
    public string $password;
    public ?string $defaultPhpVersion = null;
    public int $clusterId;
    public ?int $id = null;
    public ?int $unixId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): UnixUser
    {
        $unixUser = new self();
        $unixUser->username = Arr::get($data, 'username');
        $unixUser->password = Arr::get($data, 'password');
        $unixUser->defaultPhpVersion = Arr::get($data, 'default_php_version');
        $unixUser->unixId = Arr::get($data, 'unix_id');
        $unixUser->id = Arr::get($data, 'id');
        $unixUser->clusterId = Arr::get($data, 'cluster_id');
        $unixUser->createdAt = Arr::get($data, 'created_at');
        $unixUser->updatedAt = Arr::get($data, 'updated_at');
        return $unixUser;
    }

    public function toArray(): array
    {
        return [
            'username' => $this->username,
            'password' => $this->password,
            'default_php_version' => $this->defaultPhpVersion,
            'cluster_id' => $this->clusterId,
            'id' => $this->id,
            'unix_id' => $this->unixId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
