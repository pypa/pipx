<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

use ReflectionClass;
use ReflectionProperty;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Filter;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Enums\Limit;
use Vdhicts\Cyberfusion\ClusterApi\Enums\Sort;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ListFilterException;
use Vdhicts\HttpQueryBuilder\Builder;

class ListFilter implements Filter
{
    private ?array $availableFields = null;
    private int $skip = 0;
    private int $limit = Limit::DEFAULT_LIMIT;
    private array $filter = [];
    private array $sort = [];

    public static function forModel(Model $model): self
    {
        $reflection = new ReflectionClass($model);
        $properties = array_map(
            fn(ReflectionProperty $property) => Str::snake($property->name),
            $reflection->getProperties(ReflectionProperty::IS_PRIVATE)
        );

        return (new self())->setAvailableFields($properties);
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
        if ($limit > Limit::MAX_LIMIT) {
            $limit = Limit::MAX_LIMIT;
        }
        $this->limit = $limit;

        return $this;
    }

    public function getFilter(): array
    {
        return $this->filter;
    }

    /**
     * @param mixed $value
     * @throws ListFilterException
     */
    public function addFilter(string $field, $value): ListFilter
    {
        if ($this->hasAvailableFields() && !in_array($field, $this->availableFields)) {
            throw ListFilterException::fieldNotAvailable($field);
        }

        $this->filter[] = ['field' => $field, 'value' => $value];

        return $this;
    }

    public function setFilter(array $filter): ListFilter
    {
        foreach ($filter as $filterEntry) {
            if (Arr::has($filterEntry, 'field') && Arr::has($filterEntry, 'value')) {
                $this->addFilter($filterEntry['field'], $filterEntry['value']);
            }
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
    public function addSort(string $field, string $method = Sort::ASC): ListFilter
    {
        if (!in_array($method, Sort::AVAILABLE)) {
            throw ListFilterException::invalidSortMethod($method);
        }

        if ($this->hasAvailableFields() && !in_array($field, $this->availableFields)) {
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

    public function toQuery(): string
    {
        $builder = (new Builder())
            ->add('skip', (string)$this->skip)
            ->add('limit', (string)$this->limit);
        foreach ($this->filter as $filter) {
            $builder->add('filter', sprintf('%s:%s', $filter['field'], $filter['value']));
        }
        foreach ($this->sort as $field => $value) {
            $builder->add('sort', sprintf('%s:%s', $field, $value));
        }
        return $builder->build();
    }
}
