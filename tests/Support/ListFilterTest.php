<?php

namespace Cyberfusion\ClusterApi\Tests\Support;

use Cyberfusion\ClusterApi\Support\FilterEntry;
use Cyberfusion\ClusterApi\Support\ListFilter;
use Cyberfusion\ClusterApi\Support\SortEntry;
use PHPUnit\Framework\TestCase;

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

    public function testListFilterWithArrays()
    {
        $skip = 10;
        $limit = 5;
        $filter = [
            ['field' => 'testField', 'value' => 'testValue'],
        ];
        $sort = [
            ['field' => 'col', 'value' => 'ASC'],
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

    public function testToQueryWithArrays()
    {
        $skip = 10;
        $limit = 5;
        $filter = [
            ['field' => 'testField', 'value' => 'foo'],
            ['field' => 'testField', 'value' => 'bar'],
            ['field' => 'testField2', 'value' => 'lol'],
        ];
        $sort = [
            ['field' => 'col', 'value' => 'ASC'],
        ];

        $listFilter = (new ListFilter())
            ->setSkip($skip)
            ->setLimit($limit)
            ->setFilter($filter)
            ->setSort($sort);

        $this->assertSame(
            'skip=10&limit=5&filter=testField%3Afoo&filter=testField%3Abar&filter=testField2%3Alol&sort=col%3AASC',
            $listFilter->toQuery()
        );
    }

    public function testListFilterWithObjects()
    {
        $skip = 10;
        $limit = 5;
        $filter = [
            new FilterEntry('testField', 'testValue'),
        ];
        $sort = [
            new SortEntry('col', 'ASC'),
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

    public function testToQueryWithObjects()
    {
        $skip = 10;
        $limit = 5;
        $filter = [
            new FilterEntry('testField', 'foo'),
            new FilterEntry('testField', 'bar'),
            new FilterEntry('testField2', 'lol'),
        ];
        $sort = [
            new SortEntry('col', 'ASC'),
        ];

        $listFilter = (new ListFilter())
            ->setSkip($skip)
            ->setLimit($limit)
            ->setFilter($filter)
            ->setSort($sort);

        $this->assertSame(
            'skip=10&limit=5&filter=testField%3Afoo&filter=testField%3Abar&filter=testField2%3Alol&sort=col%3AASC',
            $listFilter->toQuery()
        );
    }
}
