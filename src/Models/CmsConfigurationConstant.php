<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;
use Cyberfusion\ClusterApi\Enums\CmsConfigurationConstantName;

class CmsConfigurationConstant extends ClusterModel implements Model
{
    private string $name;
    private mixed $value;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): CmsConfigurationConstant
    {
        Validator::value($name)
            ->valueIn(CmsConfigurationConstantName::AVAILABLE)
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getValue(): mixed
    {
        return $this->value;
    }

    public function setValue(mixed $value): CmsConfigurationConstant
    {
        $this->value = $value;

        return $this;
    }

    public function fromArray(array $data): CmsConfigurationConstant
    {
        return $this
            ->setName(Arr::get($data, 'name'))
            ->setValue(Arr::get($data, 'value'));
    }

    public function toArray(): array
    {
        return [
            'name' => $this->getName(),
            'value' => $this->getValue(),
        ];
    }
}
