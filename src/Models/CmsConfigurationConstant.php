<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;
use Cyberfusion\ClusterApi\Enums\CmsConfigurationConstantName;

class CmsConfigurationConstant extends ClusterModel implements Model
{
    private string $name;
    /** @var mixed */
    private $value;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): CmsConfigurationConstant
    {
        Validator::value($name)
            ->valueIn(CmsConfigurationConstantName::AVAILABLE)
            ->maxLength(255)
            ->validate();

        $this->name = $name;

        return $this;
    }

    /**
     * @return mixed
     */
    public function getValue()
    {
        return $this->value;
    }

    /**
     * @param mixed $value
     */
    public function setValue($value): CmsConfigurationConstant
    {
        Validator::value($value)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

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
