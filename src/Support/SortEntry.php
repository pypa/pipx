<?php

namespace Cyberfusion\ClusterApi\Support;

use Cyberfusion\ClusterApi\Enums\Sort;
use Cyberfusion\ClusterApi\Exceptions\ListFilterException;

class SortEntry
{
    private string $field;
    private string $sort;

    public function __construct(string $field, string $sort = Sort::ASC)
    {
        $this->field = $field;
        $this->sort = $sort;
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
