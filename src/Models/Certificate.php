<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class Certificate implements Model
{
    public array $commonNames = [];
    public ?string $certificate = null;
    public ?string $cachain = null;
    public ?string $privateKey = null;
    public ?int $id = null;
    public ?string $statusMessage = null;
    public ?int $clusterId = null;
    public ?string $createdAt = null;
    public ?string $updatedAt = null;

    public function fromArray(array $data): Certificate
    {
        $certificate = new self();
        $certificate->commonNames = Arr::get($data, 'common_names', []);
        $certificate->certificate = Arr::get($data, 'certificate');
        $certificate->cachain = Arr::get($data, 'ca_chain');
        $certificate->privateKey = Arr::get($data, 'private_key');
        $certificate->id = Arr::get($data, 'id');
        $certificate->statusMessage = Arr::get($data, 'status_message');
        $certificate->clusterId = Arr::get($data, 'cluster_id');
        $certificate->createdAt = Arr::get($data, 'created_at');
        $certificate->updatedAt = Arr::get($data, 'updated_at');
        return $certificate;
    }

    public function toArray(): array
    {
        return [
            'common_names' => $this->commonNames,
            'certificate' => $this->certificate,
            'ca_chain' => $this->cachain,
            'private_key' => $this->privateKey,
            'id' => $this->id,
            'status_message' => $this->statusMessage,
            'cluster_id' => $this->clusterId,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
