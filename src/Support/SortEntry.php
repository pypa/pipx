<?php

namespace Cyberfusion\ClusterApi\Support;

use Cyberfusion\ClusterApi\Enums\Sort;
use Cyberfusion\ClusterApi\Exceptions\ListFilterException;

class SortEntry
{
    public function __construct(private string $field, private string $sort = Sort::ASC)
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

    public function getSort(): string
    {
        return $this->sort;
    }

    public function setSort(string $sort): self
    {
        if (!in_array($sort, Sort::AVAILABLE)) {
            throw ListFilterException::invalidSortMethod($sort);
        }

        $this->sort = $sort;
        return $this;
    }

    public function toString(): string
    {
        return sprintf('%s:%s', $this->field, $this->sort);
    }
}
