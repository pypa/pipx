<?php

namespace Cyberfusion\ClusterApi\Tests\Support;

use Cyberfusion\ClusterApi\Enums\Sort;
use Cyberfusion\ClusterApi\Support\LogFilter;
use Illuminate\Support\Carbon;
use PHPUnit\Framework\TestCase;

class LogFilterTest extends TestCase
{
    public function testLogFilterDefaults()
    {
        $logFilter = new LogFilter();

        $this->assertNull($logFilter->getTimestamp());
        $this->assertSame(100, $logFilter->getLimit());
        $this->assertFalse($logFilter->isShowRawMessage());
        $this->assertSame(Sort::ASC, $logFilter->getSort());
    }

    public function testLogFilter()
    {
        $timestamp = Carbon::today()->subDay();
        $limit = 100;
        $showRawMessage = true;

        $logFilter = (new LogFilter())
            ->setTimestamp($timestamp)
            ->setLimit($limit)
            ->setShowRawMessage($showRawMessage)
            ->setSort(Sort::DESC);

        $this->assertSame($timestamp->format('c'), $logFilter->getTimestamp()->format('c'));
        $this->assertSame(100, $logFilter->getLimit());
        $this->assertSame($showRawMessage, $logFilter->isShowRawMessage());
        $this->assertSame(Sort::DESC, $logFilter->getSort());
    }

    public function testToQuery()
    {
        $timestamp = Carbon::today()->subDay();
        $limit = 100;
        $showRawMessage = true;

        $logFilter = (new LogFilter())
            ->setTimestamp($timestamp)
            ->setLimit($limit)
            ->setShowRawMessage($showRawMessage)
            ->setSort(Sort::DESC);

        $this->assertSame(
            'timestamp=' . $timestamp->format('Y-m-d') . 'T00%3A00%3A00%2B00%3A00&limit=100&sort=DESC&show_raw_message=1',
            $logFilter->toQuery()
        );
    }
}
