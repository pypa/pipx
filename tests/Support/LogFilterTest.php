<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Tests\Support;

use Illuminate\Support\Carbon;
use PHPUnit\Framework\TestCase;
use Vdhicts\Cyberfusion\ClusterApi\Support\LogFilter;

class LogFilterTest extends TestCase
{
    public function testLogFilterDefaults()
    {
        $logFilter = new LogFilter();

        $this->assertSame(Carbon::today()->format('c'), $logFilter->getTimestamp()->format('c'));
        $this->assertSame(100, $logFilter->getLimit());
        $this->assertFalse($logFilter->isShowRawMessage());
    }

    public function testLogFilter()
    {
        $timestamp = Carbon::today()->subDay();
        $limit = 100;
        $showRawMessage = true;

        $logFilter = (new LogFilter())
            ->setTimestamp($timestamp)
            ->setLimit($limit)
            ->setShowRawMessage($showRawMessage);

        $this->assertSame($timestamp->format('c'), $logFilter->getTimestamp()->format('c'));
        $this->assertSame(100, $logFilter->getLimit());
        $this->assertSame($showRawMessage, $logFilter->isShowRawMessage());
    }

    public function testToArray()
    {
        $logFilter = new LogFilter();

        $logFilterArray = $logFilter->toArray();

        $this->assertArrayHasKey('timestamp', $logFilterArray);
        $this->assertSame(Carbon::today()->format('c'), $logFilterArray['timestamp']);
        $this->assertArrayHasKey('limit', $logFilterArray);
        $this->assertSame(100, $logFilterArray['limit']);
        $this->assertArrayHasKey('show_raw_message', $logFilterArray);
        $this->assertFalse($logFilterArray['show_raw_message']);
    }
}
