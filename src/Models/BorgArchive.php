<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class BorgArchive extends ClusterModel implements Model
{
    private string $name;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): BorgArchive
    {
        $this->name = $name;

        return $this;
    }

    public function fromArray(array $data): BorgArchive
    {
        return $this->setName(Arr::get($data, 'name'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
        ];
    }
}
