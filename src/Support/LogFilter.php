<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

use Carbon\Carbon;
use DateTimeInterface;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Filter;
use Vdhicts\Cyberfusion\ClusterApi\Enums\Limit;
use Vdhicts\Cyberfusion\ClusterApi\Enums\Sort;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ListFilterException;

class LogFilter implements Filter
{
    private DateTimeInterface $timestamp;
    private int $limit = Limit::DEFAULT_LIMIT;
    private string $sort = Sort::SORT_ASC;
    private bool $showRawMessage = false;

    public function __construct()
    {
        $this->timestamp = Carbon::today();
    }

    public function getTimestamp(): DateTimeInterface
    {
        return $this->timestamp;
    }

    public function setTimestamp(DateTimeInterface $timestamp): LogFilter
    {
        $this->timestamp = $timestamp;

        return $this;
    }

    public function getLimit(): int
    {
        return $this->limit;
    }

    public function setLimit(int $limit): LogFilter
    {
        if ($limit > Limit::MAX_LIMIT) {
            $limit = Limit::MAX_LIMIT;
        }
        $this->limit = $limit;

        return $this;
    }

    public function getSort(): string
    {
        return $this->sort;
    }

    public function setSort(string $sort = Sort::SORT_ASC): LogFilter
    {
        if (!in_array($sort, Sort::AVAILABLE)) {
            throw ListFilterException::invalidSortMethod($sort);
        }

        $this->sort = $sort;

        return $this;
    }

    public function isShowRawMessage(): bool
    {
        return $this->showRawMessage;
    }

    public function setShowRawMessage(bool $showRawMessage): LogFilter
    {
        $this->showRawMessage = $showRawMessage;

        return $this;
    }

    public function toQuery(): string
    {
        return http_build_query([
            'timestamp' => $this->timestamp->format('c'),
            'limit' => $this->limit,
            'sort' => $this->sort,
            'show_raw_message' => $this->showRawMessage,
        ]);
    }
}
