<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use JsonSerializable;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ModelException;
use Vdhicts\Cyberfusion\ClusterApi\Exceptions\ValidationException;
use Vdhicts\Cyberfusion\ClusterApi\Support\Str;

abstract class ClusterModel implements JsonSerializable, Model
{
    /**
     * Provide fallback to allow the user of properties but still using the getters and setters.
     *
     * @param string $name
     * @return mixed
     * @throws ModelException
     */
    public function __get(string $name)
    {
        $method = sprintf('get%s', Str::studly($name));
        if (! method_exists($this, $method)) {
            throw ModelException::propertyNotAvailable($name);
        }

        return $this->$method();
    }

    /**
     * Provide fallback to allow the user of properties but still using the getters and setters.
     *
     * @param string $name
     * @param $value
     * @return void
     * @throws ModelException
     */
    public function __set(string $name, $value): void
    {
        $method = sprintf('set%s', Str::studly($name));
        if (! method_exists($this, $method)) {
            throw ModelException::propertyNotAvailable($name);
        }

        $this->$method($value);
    }

    /**
     * Performs the validation rule.
     *
     * @param mixed $value
     * @param string $type
     * @param mixed $setting
     * @return bool
     */
    private function performValidation($value, string $type, $setting): bool
    {
        switch ($type) {
            case 'length_max':
                return is_string($value) && Str::length($value) <= $setting;
            case 'pattern':
                return is_string($value) && Str::match($value, sprintf('/%s/', $setting));
            case 'in':
                return in_array($value, $setting);
            case 'in_array':
                return ! array_diff($value, $setting);
            default:
                return true;
        }
    }

    /**
     * Validate the provided value to the provided validations.
     *
     * @param mixed $value
     * @param array $validations
     * @throws ValidationException
     */
    protected function validate($value, array $validations = []): void
    {
        // When the field is nullable and the value is null no other validations are performed
        if (Arr::get($validations, 'nullable') === true && is_null($value)) {
            return;
        }

        $failedValidations = [];
        foreach ($validations as $type => $setting) {
            if (! $this->performValidation($value, $type, $setting)) {
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
    }

    /**
     * Serializes the model to a value that can be serialized with json_encode.
     *
     * @return array
     */
    public function jsonSerialize(): array
    {
        return $this->toArray();
    }
}
