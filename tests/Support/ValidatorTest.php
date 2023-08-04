<?php

namespace Cyberfusion\ClusterApi\Tests\Support;

use Cyberfusion\ClusterApi\Exceptions\ValidationException;
use Cyberfusion\ClusterApi\Support\Str;
use Cyberfusion\ClusterApi\Support\Validator;
use PHPUnit\Framework\TestCase;

class ValidatorTest extends TestCase
{
    public function testSingleValueOnly(): void
    {
        $result = Validator::value('test')
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value(['foo', 'bar'])
            ->validate();
        $this->assertTrue($result);
    }

    public function testMultipleValuesOnly(): void
    {
        $result = Validator::value(['foo', 'bar'])
            ->validate();
        $this->assertTrue($result);
    }

    public function testNullable(): void
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

    public function testNullableMultiple(): void
    {
        $result = Validator::value([null, null])
            ->each()
            ->nullable()
            ->validate();
        $this->assertTrue($result);
    }

    public function testMaxLength(): void
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

    public function testMaxLengthMultiple(): void
    {
        $result = Validator::value(['foo', 'bar'])
            ->each()
            ->maxLength(5)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([[1, 2, 3, 4, 5], [6, 7, 8]])
            ->each()
            ->maxLength(5)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['foo', 'foo-bar'])
            ->each()
            ->maxLength(3)
            ->validate();
    }

    public function testMinLength(): void
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

    public function testMinLengthMultiple(): void
    {
        $result = Validator::value(['foo', 'bar'])
            ->each()
            ->minLength(2)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([[1, 2], [3, 4, 5]])
            ->each()
            ->minLength(2)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['foo', ''])
            ->each()
            ->minLength(2)
            ->validate();
    }

    public function testMaxAmount(): void
    {
        $result = Validator::value(100)
            ->maxAmount(500)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([1, 2, 3, 4, 5])
            ->maxAmount(10)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(5)
            ->maxAmount(2)
            ->validate();
    }

    public function testMaxAmountMultiple(): void
    {
        $result = Validator::value([2, 5])
            ->each()
            ->maxAmount(10)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([[1, 2, 3, 4, 5], [6, 7, 8]])
            ->each()
            ->maxAmount(10)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value([2, 5])
            ->each()
            ->maxAmount(4)
            ->validate();
    }

    public function testMinAmount(): void
    {
        $result = Validator::value(5)
            ->minAmount(2)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([1, 2])
            ->minAmount(0)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(0)
            ->minAmount(2)
            ->validate();
    }

    public function testMinAmountMultiple(): void
    {
        $result = Validator::value([2, 5])
            ->each()
            ->minAmount(1)
            ->validate();
        $this->assertTrue($result);

        $result = Validator::value([[1, 2], [3, 4, 5]])
            ->each()
            ->minAmount(1)
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value([1, 2])
            ->each()
            ->minAmount(2)
            ->validate();
    }

    public function testPattern(): void
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

    public function testPatternMultiple(): void
    {
        $result = Validator::value(['foo', 'bar'])
            ->each()
            ->pattern('^[a-z]+$')
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['123', 'test'])
            ->each()
            ->pattern('^[0-9]+$')
            ->validate();
    }

    public function testValueIn(): void
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

    public function testValueInMultiple(): void
    {
        $result = Validator::value(['test', 'foo'])
            ->each()
            ->valueIn(['test', 'foo', 'bar'])
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['foo', 'test'])
            ->each()
            ->valueIn(['foo', 'bar'])
            ->validate();
    }

    public function testValuesIn(): void
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

    public function testValuesInMultiple(): void
    {
        $result = Validator::value([['foo', 'bar'], ['test', 'bar']])
            ->each()
            ->valuesIn(['test', 'foo', 'bar'])
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value([['foo'], ['bar', 'test']])
            ->each()
            ->valuesIn(['foo', 'bar'])
            ->validate();
    }

    public function testUnique(): void
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

    public function testUniqueMultiple(): void
    {
        $result = Validator::value([['foo', 'bar'], ['foo', 'bar']])
            ->each()
            ->unique()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value([['test', 'foo', 'bar'], ['test', 'foo', 'bar', 'test']])
            ->each()
            ->unique()
            ->validate();
    }

    public function testIp(): void
    {
        $result = Validator::value(['127.0.0.1', '192.168.1.1'])
            ->each()
            ->ip()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['127.0.0.1', 'foo'])
            ->each()
            ->ip()
            ->validate();
    }

    public function testEmail(): void
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

    public function testEmailMultiple(): void
    {
        $result = Validator::value(['foo@bar.com', 'bar@foo.com'])
            ->each()
            ->email()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['foo@bar.com', 'foo'])
            ->each()
            ->email()
            ->validate();
    }

    public function testPath(): void
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

    public function testPathMultiple(): void
    {
        $result = Validator::value(['/home/test', '/home/foobar'])
            ->each()
            ->path()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['/home', 123])
            ->each()
            ->path()
            ->validate();
    }

    public function testUuid(): void
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

    public function testUuidMultiple(): void
    {
        $result = Validator::value([Str::uuid(), Str::uuid()])
            ->each()
            ->uuid()
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value([Str::uuid(), 'foo'])
            ->each()
            ->uuid()
            ->validate();
    }

    public function testEndsWith(): void
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

    public function testEndsWithMultiple(): void
    {
        $result = Validator::value(['test.js', 'app.js'])
            ->each()
            ->endsWith('.js')
            ->validate();
        $this->assertTrue($result);

        $this->expectException(ValidationException::class);
        Validator::value(['test.js', 2])
            ->each()
            ->endsWith('.js')
            ->validate();
    }
}
