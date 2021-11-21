<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

use Vdhicts\Cyberfusion\ClusterApi\Contracts\Filter;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ListFilterException;
use Vdhicts\HttpQueryBuilder\Builder;

class ListFilter implements Filter
{
    private const MAX_LIMIT = 1000;
    public const SORT_ASC = 'ASC';
    public const SORT_DESC = 'DESC';

    private ?array $availableFields = null;
    private int $skip = 0;
    private int $limit = 100;
    private array $filter = [];
    private array $sort = [];

    public static function forModel(Model $model): self
    {
        return (new self())->setAvailableFields($model->toArray());
    }

    public function getAvailableFields(): ?array
    {
        return $this->availableFields;
    }

    private function hasAvailableFields(): bool
    {
        return !is_null($this->availableFields);
    }

    public function setAvailableFields(?array $availableFields): ListFilter
    {
        $this->availableFields = $availableFields;

        return $this;
    }

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

    public function addFilter(string $field, $value): ListFilter
    {
        if ($this->hasAvailableFields() && !Arr::has($this->availableFields, $field)) {
            throw ListFilterException::fieldNotAvailable($field);
        }

        $this->filter[$field] = $value;

        return $this;
    }

    public function setFilter(array $filter): ListFilter
    {
        foreach ($filter as $field => $value) {
            $this->addFilter($field, $value);
        }

        return $this;
    }

    public function getSort(): array
    {
        return $this->sort;
    }

    /**
     * @throws ListFilterException
     */
    public function addSort(string $field, string $method = self::SORT_ASC): ListFilter
    {
        if (!in_array($method, [self::SORT_ASC, self::SORT_DESC])) {
            throw ListFilterException::invalidSortMethod($method);
        }

        if ($this->hasAvailableFields() && !Arr::has($this->availableFields, $field)) {
            throw ListFilterException::fieldNotAvailable($field);
        }

        $this->sort[$field] = $method;

        return $this;
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
            'filter' => Arr::colonSeparatedValues($this->filter),
            'sort' => Arr::colonSeparatedValues($this->sort),
        ];
    }

    public function toQuery(): string
    {
        $builder = (new Builder())
            ->add('skip', $this->skip)
            ->add('limit', $this->limit);
        foreach ($this->filter as $field => $value) {
            $builder->add('filter', sprintf('%s:%s', $field, $value));
        }
        foreach ($this->sort as $field => $value) {
            $builder->add('sort', sprintf('%s:%s', $field, $value));
        }
        return $builder->build();
    }
}
