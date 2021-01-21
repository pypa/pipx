<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Tests;

use PHPUnit\Framework\TestCase;
use Vdhicts\Cyberfusion\ClusterApi\Configuration;

class ConfigurationTest extends TestCase
{
    public function testChangingUrl()
    {
        $configuration = new Configuration();

        $this->assertSame('https://cluster-api.cyberfusion.nl/api/v1/', $configuration->getUrl());

        $configuration->setUrl('foo://bar');

        $this->assertSame('foo://bar', $configuration->getUrl());
    }

    public function testWithCredentials()
    {
        $configuration = Configuration::withCredentials('foo', 'bar');

        $this->assertSame('foo', $configuration->getUsername());
        $this->assertSame('bar', $configuration->getPassword());
        $this->assertTrue($configuration->hasCredentials());
        $this->assertFalse($configuration->hasAccessToken());
    }

    public function testWithAccessToken()
    {
        $configuration = Configuration::withAccessToken('fooBar');

        $this->assertSame('fooBar', $configuration->getAccessToken());
        $this->assertFalse($configuration->hasCredentials());
        $this->assertTrue($configuration->hasAccessToken());
    }
}
