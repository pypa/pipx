<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

use Vdhicts\Cyberfusion\ClusterApi\Contracts\Filter;
use Vdhicts\HttpQueryBuilder\Builder;

class ListFilter implements Filter
{
    private const MAX_LIMIT = 1000;

    private int $skip = 0;
    private int $limit = 100;
    private array $filter = [];
    private array $sort = [];

    public function getSkip(): int
    {
        return $this->skip;
    }

    public function setSkip(int $skip): ListFilter
    {
        $this->skip = $skip;

        return $this;
    }

    public function getLimit(): int
    {
        return $this->limit;
    }

    public function setLimit(int $limit): ListFilter
    {
        if ($limit > self::MAX_LIMIT) {
            $limit = self::MAX_LIMIT;
        }
        $this->limit = $limit;

        return $this;
    }

    public function getFilter(): array
    {
        return $this->filter;
    }

    public function setFilter(array $filter): ListFilter
    {
        $this->filter = $filter;

        return $this;
    }

    public function getSort(): array
    {
        return $this->sort;
    }

    public function setSort(array $sort): ListFilter
    {
        $this->sort = $sort;

        return $this;
    }

    public function toArray(): array
    {
        return [
            'skip' => $this->skip,
            'limit' => $this->limit,
            'filter' => $this->filter,
            'sort' => $this->sort,
        ];
    }

    public function toQuery(): string
    {
        $builder = (new Builder())
            ->add('skip', $this->skip)
            ->add('limit', $this->limit);
        foreach ($this->filter as $filter) {
            $builder->add('filter', $filter);
        }
        foreach ($this->sort as $sort) {
            $builder->add('sort', $sort);
        }
        return $builder->build();
    }
}
