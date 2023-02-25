<?php

namespace Cyberfusion\ClusterApi\Support;

use Cyberfusion\ClusterApi\Exceptions\ValidationException;
use Ramsey\Uuid\Uuid;

class Validator
{
    private const NULLABLE = 'nullable';
    private const MAX_LENGTH = 'length_max';
    private const MIN_LENGTH = 'length_min';
    private const PATTERN = 'pattern';
    private const VALUE_IN = 'in_list';
    private const VALUES_IN = 'part_of_list';
    private const UNIQUE = 'unique_list';
    private const IP = 'ip';
    private const EMAIL = 'email';
    private const PATH = 'path';
    private const UUID = 'uuid';
    private const ENDS_WITH = 'ends_with';
    private bool $multiple = false;
    private array $validations = [];

    public static function value(mixed $value): self
    {
        return new self($value);
    }

    private function __construct(private mixed $value)
    {
    }

    public function each(): self
    {
        $this->multiple = true;
        return $this;
    }

    public function nullable(): self
    {
        $this->validations[self::NULLABLE] = true;
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

    public function path(): self
    {
        $this->validations[self::PATH] = true;
        return $this;
    }

    public function uuid(): self
    {
        $this->validations[self::UUID] = true;
        return $this;
    }

    public function endsWith(string $needle): self
    {
        $this->validations[self::ENDS_WITH] = $needle;
        return $this;
    }

    private function performValidation(string $type, $setting, $value): bool
    {
        // When the field is nullable and the value is null no other validations need to be performed
        if (is_null($value) && Arr::has($this->validations, self::NULLABLE)) {
            return true;
        }

        switch ($type) {
            case self::MAX_LENGTH:
                return
                    (is_string($value) && Str::length($value) <= $setting) ||
                    (is_array($value) && count($value) <= $setting);
            case self::MIN_LENGTH:
                return
                    (is_string($value) && Str::length($value) >= $setting) ||
                    (is_array($value) && count($value) >= $setting);
            case self::PATTERN:
                return is_string($value) && Str::doesMatch($value, sprintf('/%s/', $setting));
            case self::VALUE_IN:
                return in_array($value, $setting);
            case self::VALUES_IN:
                return !array_diff($value, $setting);
            case self::UNIQUE:
                return is_array($value) && count(array_unique($value)) === count($value);
            case self::IP:
                return filter_var($value, FILTER_VALIDATE_IP) !== false;
            case self::EMAIL:
                return filter_var($value, FILTER_VALIDATE_EMAIL) !== false;
            case self::PATH:
                // Check type
                if (!is_string($value)) {
                    return false;
                }

                // Check length of total string
                if (strlen($value) >= 4096) {
                    return false;
                }

                // Check length of each element
                $elements = explode('/', $value);

                foreach ($elements as $element) {
                    if (strlen($element) <= 255) {
                        continue;
                    }

                    return false;
                }

                return true;
            case self::UUID:
                return Uuid::isValid($value);
            case self::ENDS_WITH:
                return is_string($value) && Str::endsWith($value, $setting);
            default:
                return true;
        }
    }

    /**
     * @throws ValidationException
     */
    public function validate(): bool
    {
        $sources = $this->multiple && is_array($this->value)
            ? $this->value
            : [$this->value];

        $failedValidations = [];
        foreach ($sources as $source) {
            foreach ($this->validations as $type => $setting) {
                $isValid = $this->performValidation($type, $setting, $source);

                if (!$isValid) {
                    $failedValidations[] = sprintf(
                        '%s: %s failed on %s',
                        $type,
                        is_array($setting)
                            ? implode(';', $setting)
                            : $setting,
                        var_export($source, true)
                    );
                }
            }
        }

        if (count($failedValidations) !== 0) {
            throw ValidationException::validationFailed($failedValidations);
        }

        return true;
    }
}
