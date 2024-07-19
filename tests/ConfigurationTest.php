<?php

namespace Cyberfusion\ClusterApi\Tests;

use Cyberfusion\ClusterApi\Configuration;
use PHPUnit\Framework\TestCase;

class ConfigurationTest extends TestCase
{
    public function testChangingUrl(): void
    {
        $configuration = new Configuration();

        $this->assertSame('https://core-api.cyberfusion.io/api/v1/', $configuration->getUrl());

        $configuration->setUrl('foo://bar');

        $this->assertSame('foo://bar', $configuration->getUrl());
    }

    public function testWithCredentials(): void
    {
        $configuration = Configuration::withCredentials('foo', 'bar');

        $this->assertSame('foo', $configuration->getUsername());
        $this->assertSame('bar', $configuration->getPassword());
        $this->assertTrue($configuration->hasCredentials());
        $this->assertFalse($configuration->hasAccessToken());
    }

    public function testWithAccessToken(): void
    {
        $configuration = Configuration::withAccessToken('fooBar');

        $this->assertSame('fooBar', $configuration->getAccessToken());
        $this->assertFalse($configuration->hasCredentials());
        $this->assertTrue($configuration->hasAccessToken());
    }
}
