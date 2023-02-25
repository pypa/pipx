<?php

namespace Cyberfusion\ClusterApi\Support;

class FilterEntry
{
    public function __construct(private string $field, private mixed $value)
    {
    }

    public function getField(): string
    {
        return $this->field;
    }

    public function setField(string $field): self
    {
        $this->field = $field;
        return $this;
    }

    public function getValue(): mixed
    {
        return $this->value;
    }

    public function setValue(mixed $value): self
    {
        $this->value = $value;
        return $this;
    }

    public function toString(): string
    {
        return sprintf('%s:%s', $this->field, $this->value);
    }
}
