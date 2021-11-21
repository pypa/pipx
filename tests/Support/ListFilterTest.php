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
            ['field' => 'testField', 'value' => 'testValue'],
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

    public function testToQuery()
    {
        $skip = 10;
        $limit = 5;
        $filter = [
            ['field' => 'testField', 'value' => 'foo'],
            ['field' => 'testField', 'value' => 'bar'],
            ['field' => 'testField2', 'value' => 'lol'],
        ];
        $sort = [
            'col:ASC',
        ];

        $listFilter = (new ListFilter())
            ->setSkip($skip)
            ->setLimit($limit)
            ->setFilter($filter)
            ->setSort($sort);

        $this->assertSame(
            'skip=10&limit=5&filter=testField%3Afoo&filter=testField%3Abar&filter=testField2%3Alol&sort=0%3Acol%3AASC',
            $listFilter->toQuery()
        );
    }
}
