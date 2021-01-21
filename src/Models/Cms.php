<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Cms implements Model
{
    public string $name;
    public int $virtualHostId;
    public int $id;
    public int $clusterId;
    public string $createdAt;
    public string $updatedAt;

    public function fromArray(array $data): Cms
    {
        $cms = new self();
        $cms->name = Arr::get($data, 'name');
        $cms->virtualHostId = Arr::get($data, 'virtual_host_id');
        $cms->id = Arr::get($data, 'id');
        $cms->clusterId = Arr::get($data, 'cluster_id');
        $cms->createdAt = Arr::get($data, 'created_at');
        $cms->updatedAt = Arr::get($data, 'updated_at');
        return $cms;
    }

    public function toArray(): array
    {
        return [
            'name' => $this->name,
            'virtual_host_id' => $this->virtualHostId,
            'id' => $this->id,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
