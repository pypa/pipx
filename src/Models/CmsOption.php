<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Support\Validator;
use Cyberfusion\ClusterApi\Enums\CmsOptionName;

class CmsOption extends ClusterModel implements Model
{
    private string $name;
    /** @var mixed */
    private $value;

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): CmsOption
    {
        Validator::value($name)
            ->valueIn(CmsOptionName::AVAILABLE)
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
    public function setValue($value): CmsOption
    {
        $this->value = $value;

        return $this;
    }

    public function fromArray(array $data): CmsOption
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
