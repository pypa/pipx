<?php

namespace Cyberfusion\ClusterApi\Tests\Support;

use PHPUnit\Framework\TestCase;
use Cyberfusion\ClusterApi\Exceptions\ValidationException;
use Cyberfusion\ClusterApi\Support\Str;
use Cyberfusion\ClusterApi\Support\Validator;

class ValidatorTest extends TestCase
{
    public function testValueOnly()
    {
        $result = Validator::value('test')
            ->validate();
        $this->assertTrue($result);
    }

    public function testNullable()
    {
        $result = Validator::value(null)
            ->nullable()
            ->email()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(null)
            ->email()
            ->validate();
    }

    public function testMaxLength()
    {
        $result = Validator::value('test')
            ->maxLength(5)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([1, 2, 3, 4, 5])
            ->maxLength(5)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('test')
            ->maxLength(2)
            ->validate();
    }

    public function testMinLength()
    {
        $result = Validator::value('test')
            ->minLength(2)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([1, 2])
            ->minLength(2)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('')
            ->minLength(2)
            ->validate();
    }

    public function testPattern()
    {
        $result = Validator::value('test')
            ->pattern('^[a-z]+$')
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('test')
            ->pattern('^[0-9]+$')
            ->validate();
    }

    public function testValueIn()
    {
        $result = Validator::value('test')
            ->valueIn(['test', 'foo', 'bar'])
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('test')
            ->valueIn(['foo', 'bar'])
            ->validate();
    }

    public function testValuesIn()
    {
        $result = Validator::value(['foo', 'bar'])
            ->valuesIn(['test', 'foo', 'bar'])
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['test', 'foo'])
            ->valuesIn(['foo', 'bar'])
            ->validate();
    }

    public function testUnique()
    {
        $result = Validator::value(['foo', 'bar'])
            ->unique()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['test', 'foo', 'bar', 'test'])
            ->unique()
            ->validate();
    }

    public function testIp()
    {
        $result = Validator::value('127.0.0.1')
            ->ip()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('foo')
            ->ip()
            ->validate();
    }

    public function testEmail()
    {
        $result = Validator::value('foo@bar.com')
            ->email()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('foo')
            ->email()
            ->validate();
    }

    public function testPath()
    {
        $result = Validator::value('/home/test')
            ->path()
            ->validate();
        $this->assertTrue($result);

        // Total string exceeds max length
        $this->expectException(ValidationException::class);
        Validator::value(sprintf('/%s', bin2hex(random_bytes($length = 4097))))
            ->path()
            ->validate();

        // Path element exceeds max length
        $this->expectException(ValidationException::class);
        Validator::value(sprintf('/home/%s', bin2hex(random_bytes($length = 256))))
            ->path()
            ->validate();
    }

    public function testUuid()
    {
        $result = Validator::value(Str::uuid())
            ->uuid()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value('foo')
            ->uuid()
            ->validate();
    }

    public function testEndsWith()
    {
        $result = Validator::value('test.js')
            ->endsWith('.js')
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(2)
            ->endsWith('.js')
            ->validate();
    }
}
