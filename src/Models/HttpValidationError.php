<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Arr;

class HttpValidationError extends ClusterModel implements Model
{
    private array $detail = [];

    public function getDetail(): array
    {
        return $this->detail;
    }

    public function setDetail(array $detail): self
    {
        $this->detail = $detail;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this->setDetail(array_map(
            function (array $detail) {
                return (new ValidationError())->fromArray($detail);
            },
            Arr::get($data, 'detail', [])
        ));
    }

    public function toArray(): array
    {
        return [
            'detail' => $this->getDetail(),
        ];
    }
}
