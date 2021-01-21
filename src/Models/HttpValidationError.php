<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class HttpValidationError implements Model
{
    public array $detail = [];

    public function fromArray(array $data): HttpValidationError
    {
        $httpValidationError = new self();
        $httpValidationError->detail = array_map(
            function (array $detail) {
                return (new ValidationError())->fromArray($detail);
            },
            Arr::get($data, 'detail', [])
        );
        return $httpValidationError;
    }

    public function toArray(): array
    {
        return [
            'detail' => $this->detail,
        ];
    }
}
