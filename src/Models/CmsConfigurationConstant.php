<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Enums\CmsConfigurationConstantName;
use Cyberfusion\ClusterApi\Exceptions\ValidationException;
use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class CmsConfigurationConstant extends ClusterModel
{
    private string $name;
    private mixed $value;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): self
    {
        Validator::value($name)
            ->valueIn(CmsConfigurationConstantName::AVAILABLE)
            ->maxLength(255)
            ->validate();

        $this->name = $name;

        return $this;
    }

    public function getValue(): mixed
    {
        return $this->value;
    }

    /**
     * @throws ValidationException
     */
    public function setValue(mixed $value): self
    {
        Validator::value($value)
            ->maxLength(255)
            ->pattern('^[ -~]+$')
            ->validate();

        $this->value = $value;

        return $this;
    }

    public function fromArray(array $data): self
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
