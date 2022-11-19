<?php

namespace Cyberfusion\ClusterApi\Support;

use ReflectionClass;
use ReflectionException;
use ReflectionProperty;
use Cyberfusion\ClusterApi\Contracts\Filter;
use Cyberfusion\ClusterApi\Contracts\Model;
use Cyberfusion\ClusterApi\Enums\Limit;
use Cyberfusion\ClusterApi\Exceptions\ListFilterException;
use Vdhicts\HttpQueryBuilder\Builder;

class ListFilter implements Filter
{
    private ?array $availableFields = null;
    private int $skip = 0;
    private int $limit = Limit::DEFAULT_LIMIT;
    /** @var array<FilterEntry> */
    private array $filter = [];
    /** @var array<SortEntry> */
    private array $sort = [];

    /**
     * @param Model|class-string $model
     * @throws ListFilterException
     */
    public static function forModel($model): self
    {
        if (! is_subclass_of($model, Model::class)) {
            throw ListFilterException::invalidModel();
        }

        try {
            $reflection = new ReflectionClass($model);
            $properties = array_map(
                fn(ReflectionProperty $property) => Str::snake($property->name),
                $reflection->getProperties(ReflectionProperty::IS_PRIVATE)
            );
        } catch (ReflectionException $exception) {
            throw ListFilterException::unableToDetermineFields($exception);
        }

        return (new self())->setAvailableFields($properties);
    }

    /**
     * @param array<FilterEntry> $filters
     * @param array<SortEntry> $sort
     * @throws ListFilterException
     */
    public function __construct(array $filters = [], array $sort = [])
    {
        $this
            ->setFilter($filters)
            ->setSort($sort);
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
     * @throws ListFilterException
     */
    public function addFilter(FilterEntry $entry): ListFilter
    {
        if ($this->hasAvailableFields() && !in_array($entry->getField(), $this->availableFields)) {
            throw ListFilterException::fieldNotAvailable($entry->getField());
        }

        $this->filter[] = $entry;

        return $this;
    }

    /**
     * @throws ListFilterException
     */
    public function setFilter(array $filterEntries): ListFilter
    {
        foreach ($filterEntries as $filterEntry) {
            if (is_array($filterEntry)) {
                $filterEntry = new FilterEntry($filterEntry['field'], $filterEntry['value']);
            }

            $this->addFilter($filterEntry);
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
    public function addSort(SortEntry $entry): ListFilter
    {
        if ($this->hasAvailableFields() && !in_array($entry->getField(), $this->availableFields)) {
            throw ListFilterException::fieldNotAvailable($entry->getField());
        }

        $this->sort[] = $entry;

        return $this;
    }

    /**
     * @throws ListFilterException
     */
    public function setSort(array $sortEntries): ListFilter
    {
        foreach ($sortEntries as $sortEntry) {
            if (is_array($sortEntry)) {
                $sortEntry = new SortEntry($sortEntry['field'], $sortEntry['value']);
            }

            $this->addSort($sortEntry);
        }

        return $this;
    }

    public function toQuery(): string
    {
        $builder = (new Builder())
            ->add('skip', (string)$this->skip)
            ->add('limit', (string)$this->limit);
        foreach ($this->filter as $entry) {
            $builder->add('filter', $entry->toString());
        }
        foreach ($this->sort as $entry) {
            $builder->add('sort', $entry->toString());
        }
        return $builder->build();
    }
}
