<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Tests\Support;

use PHPUnit\Framework\TestCase;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class ListFilterTest extends TestCase
{
    public function testListFilterDefaults()
    {
        $listFilter = new ListFilter();

        $this->assertSame(0, $listFilter->getSkip());
        $this->assertSame(100, $listFilter->getLimit());
        $this->assertIsArray($listFilter->getFilter());
        $this->assertCount(0, $listFilter->getFilter());
        $this->assertIsArray($listFilter->getSort());
        $this->assertCount(0, $listFilter->getSort());
    }

    public function testListFilter()
    {
        $skip = 10;
        $limit = 5;
        $filter = [
            'key:value',
        ];
        $sort = [
            'col:ASC',
        ];

        $listFilter = (new ListFilter())
            ->setSkip($skip)
            ->setLimit($limit)
            ->setFilter($filter)
            ->setSort($sort);

        $this->assertSame($skip, $listFilter->getSkip());
        $this->assertSame($limit, $listFilter->getLimit());
        $this->assertIsArray($listFilter->getFilter());
        $this->assertCount(1, $listFilter->getFilter());
        $this->assertIsArray($listFilter->getSort());
        $this->assertCount(1, $listFilter->getSort());
    }

    public function testToArray()
    {
        $listFilter = new ListFilter();

        $listFilterArray = $listFilter->toArray();

        $this->assertArrayHasKey('skip', $listFilterArray);
        $this->assertSame(0, $listFilterArray['skip']);
        $this->assertArrayHasKey('limit', $listFilterArray);
        $this->assertSame(100, $listFilterArray['limit']);
        $this->assertArrayHasKey('filter', $listFilterArray);
        $this->assertIsArray($listFilterArray['filter']);
        $this->assertArrayHasKey('sort', $listFilterArray);
        $this->assertIsArray($listFilterArray['sort']);
    }
}
