<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

use Ramsey\Uuid\Uuid;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ValidationException;

class Validator
{
    private const NULLABLE = 'nullable';
    private const POSITIVE_INTEGER = 'positive_integer';
    private const MAX_LENGTH = 'length_max';
    private const MIN_LENGTH = 'length_min';
    private const PATTERN = 'pattern';
    private const VALUE_IN = 'in_list';
    private const VALUES_IN = 'part_of_list';
    private const UNIQUE = 'unique_list';
    private const IP = 'ip';
    private const EMAIL = 'email';
    private const UUID = 'uuid';

    /** @var mixed */
    private $value;
    private array $validations = [];

    /**
     * @param mixed $value
     */
    public static function value($value): Validator
    {
        return new self($value);
    }

    /**
     * @param mixed $value
     */
    private function __construct($value)
    {
        $this->value = $value;
    }

    public function nullable(): self
    {
        $this->validations[self::NULLABLE] = true;
        return $this;
    }

    public function positiveInteger(): self
    {
        $this->validations[self::POSITIVE_INTEGER] = true;
        return $this;
    }

    public function maxLength(int $maxLength): self
    {
        $this->validations[self::MAX_LENGTH] = $maxLength;
        return $this;
    }

    public function minLength(int $minLength): self
    {
        $this->validations[self::MIN_LENGTH] = $minLength;
        return $this;
    }

    public function pattern(string $pattern): self
    {
        $this->validations[self::PATTERN] = $pattern;
        return $this;
    }

    public function valueIn(array $list): self
    {
        $this->validations[self::VALUE_IN] = $list;
        return $this;
    }

    public function valuesIn(array $list): self
    {
        $this->validations[self::VALUES_IN] = $list;
        return $this;
    }

    public function unique(): self
    {
        $this->validations[self::UNIQUE] = true;
        return $this;
    }

    public function ip(): self
    {
        $this->validations[self::IP] = true;
        return $this;
    }

    public function email(): self
    {
        $this->validations[self::EMAIL] = true;
        return $this;
    }

    public function uuid(): self
    {
        $this->validations[self::UUID] = true;
        return $this;
    }

    private function isNullable(): bool
    {
        return Arr::has($this->validations, self::NULLABLE);
    }

    private function performValidation(string $type, $setting): bool
    {
        switch ($type) {
            case self::POSITIVE_INTEGER:
                return is_integer($this->value) && $this->value >= 0;
            case self::MAX_LENGTH:
                return
                    (is_string($this->value) && Str::length($this->value) <= $setting) ||
                    (is_array($this->value) && count($this->value) <= $setting);
            case self::MIN_LENGTH:
                return
                    (is_string($this->value) && Str::length($this->value) >= $setting) ||
                    (is_array($this->value) && count($this->value) >= $setting);
            case self::PATTERN:
                return is_string($this->value) && Str::doesMatch($this->value, sprintf('/%s/', $setting));
            case self::VALUE_IN:
                return in_array($this->value, $setting);
            case self::VALUES_IN:
                return !array_diff($this->value, $setting);
            case self::UNIQUE:
                return is_array($this->value) && count(array_unique($this->value)) === count($this->value);
            case self::IP:
                return filter_var($this->value, FILTER_VALIDATE_IP) !== false;
            case self::EMAIL:
                return filter_var($this->value, FILTER_VALIDATE_EMAIL) !== false;
            case self::UUID:
                return Uuid::isValid($this->value);
            default:
                return true;
        }
    }

    /**
     * @throws ValidationException
     */
    public function validate(): bool
    {
        // When the field is nullable and the value is null no other validations are performed
        if ($this->isNullable() && is_null($this->value)) {
            return true;
        }

        $failedValidations = [];
        foreach ($this->validations as $type => $setting) {
            $isValid = $this->performValidation($type, $setting);

            if (!$isValid) {
                $failedValidations[] = sprintf(
                    '%s: %s',
                    $type,
                    is_array($setting)
                        ? implode(';', $setting)
                        : $setting
                );
            }
        }

        if (count($failedValidations) !== 0) {
            throw ValidationException::validationFailed($failedValidations);
        }

        return true;
    }
}
