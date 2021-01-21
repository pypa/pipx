<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class ValidationError implements Model
{
    public array $loc = [];
    public string $msg;
    public string $type;

    public function fromArray(array $data): ValidationError
    {
        $validationError = new self();
        $validationError->loc = Arr::get($data, 'loc', []);
        $validationError->msg = Arr::get($data, 'msg');
        $validationError->type = Arr::get($data, 'type');
        return $validationError;
    }

    public function toArray(): array
    {
        return [
            'loc' => $this->loc,
            'msg' => $this->msg,
            'type' => $this->type,
        ];
    }
}
