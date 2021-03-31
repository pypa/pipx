<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class HttpValidationError extends ClusterModel implements Model
{
    private array $detail = [];

    public function getDetail(): array
    {
        return $this->detail;
    }

    public function setDetail(array $detail): HttpValidationError
    {
        $this->detail = $detail;

        return $this;
    }

    public function fromArray(array $data): HttpValidationError
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
