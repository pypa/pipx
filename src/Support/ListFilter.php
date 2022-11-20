<?php

namespace Cyberfusion\ClusterApi\Support;

use Cyberfusion\ClusterApi\Enums\Sort;
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
    private const REQUIRED_KEYS = [
        'field',
        'value',
    ];

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

    /**
     * @return array<FilterEntry>
     */
    public function getFilter(): array
    {
        return $this->filter;
    }

    /**
     * @throws ListFilterException
     */
    public function filter(FilterEntry $filterEntry): ListFilter
    {
        if ($this->hasAvailableFields() && !in_array($filterEntry->getField(), $this->availableFields)) {
            throw ListFilterException::fieldNotAvailable($filterEntry->getField());
        }

        $this->filter[] = $filterEntry;
        return $this;
    }

    /**
     * @throws ListFilterException
     */
    public function addFilter(string $field, $value): ListFilter
    {
        return $this->filter(new FilterEntry($field, $value));
    }

    /**
     * @throws ListFilterException
     */
    public function setFilter(array $filterEntries): ListFilter
    {
        foreach ($filterEntries as $filterEntry) {
            if ($filterEntry instanceof FilterEntry) {
                $this->filter($filterEntry);
                continue;
            }

            if (!is_array($filterEntry)) {
                throw ListFilterException::invalidTypeInArray(gettype($filterEntry));
            }

            if (! Arr::keysExists(self::REQUIRED_KEYS, $filterEntry)) {
                throw ListFilterException::arrayEntryKeysInvalid(self::REQUIRED_KEYS);
            }

            $this->filter(new FilterEntry($filterEntry['field'], $filterEntry['value']));
        }

        return $this;
    }

    /**
     * @return array<SortEntry>
     */
    public function getSort(): array
    {
        return $this->sort;
    }

    /**
     * @throws ListFilterException
     */
    public function sort(SortEntry $sortEntry): ListFilter
    {
        if ($this->hasAvailableFields() && !in_array($sortEntry->getField(), $this->availableFields)) {
            throw ListFilterException::fieldNotAvailable($sortEntry->getField());
        }

        $this->sort[] = $sortEntry;
        return $this;
    }

    /**
     * @throws ListFilterException
     */
    public function addSort(string $field, string $method = Sort::ASC): ListFilter
    {
        return $this->sort(new SortEntry($field, $method));
    }

    /**
     * @throws ListFilterException
     */
    public function setSort(array $sortEntries): ListFilter
    {
        foreach ($sortEntries as $sortEntry) {
            if ($sortEntry instanceof SortEntry) {
                $this->sort($sortEntry);
                continue;
            }

            if (!is_array($sortEntry)) {
                throw ListFilterException::invalidTypeInArray(gettype($sortEntry));
            }

            if (!Arr::keysExists(self::REQUIRED_KEYS, $sortEntry)) {
                throw ListFilterException::arrayEntryKeysInvalid(self::REQUIRED_KEYS);
            }

            $this->sort(new SortEntry($sortEntry['field'], $sortEntry['value']));
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
