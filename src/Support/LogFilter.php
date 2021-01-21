<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

use Carbon\Carbon;
use DateTimeInterface;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Filter;

class LogFilter implements Filter
{
    private DateTimeInterface $timestamp;
    private int $limit = 100;
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
        $this->limit = $limit;

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

    public function toArray(): array
    {
        return [
            'timestamp' => $this->timestamp->format('c'),
            'limit' => $this->limit,
            'show_raw_message' => $this->showRawMessage,
        ];
    }
}
