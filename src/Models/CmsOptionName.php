<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Vdhicts\Cyberfusion\ClusterApi\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class CmsOption extends ClusterModel implements Model
{
    private mixed $value;

    public function getValue(): mixed
    {
        return $this->value;
    }

    public function setValue(mixed $value): CmsOption
    {
        $this->value = $value;

        return $this;
    }

    public function fromArray(array $data): CmsOption
    {
        return $this
            ->setValue(Arr::get($data, 'value'));
    }

    public function toArray(): array
    {
        return [
            'value' => $this->getValue(),
        ];
    }
}
