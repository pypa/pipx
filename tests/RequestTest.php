<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Tests;

use PHPUnit\Framework\TestCase;
use Vdhicts\Cyberfusion\ClusterApi\Request;

class RequestTest extends TestCase
{
    public function testRequestDefaults()
    {
        $request = new Request();

        $this->assertSame(Request::METHOD_GET, $request->getMethod());
        $this->assertTrue($request->authenticationRequired());
    }

    public function testRequest()
    {
        $url = '';
        $requiresAuthentication = false;
        $method = Request::METHOD_PATCH;

        $request = (new Request())
            ->setUrl($url)
            ->setAuthenticationRequired($requiresAuthentication)
            ->setMethod($method)
            ->setBody(['foo' => 'bar']);

        $this->assertSame($url, $request->getUrl());
        $this->assertSame($requiresAuthentication, $request->authenticationRequired());
        $this->assertSame($method, $request->getMethod());
        $this->assertCount(1, $request->getBody());
    }
}
