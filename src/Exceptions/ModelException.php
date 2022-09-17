<?php

namespace Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class ModelException extends ClusterApiException
{
    public static function propertyNotAvailable(string $property, Throwable $previous = null): ModelException
    {
        return new self(
            sprintf('The property `%s` is not available for this model', $property),
            self::MODEL_PROPERTY_NOT_AVAILABLE,
            $previous
        );
    }

    public static function engineSetAfterPassword(Throwable $previous = null): ModelException
    {
        return new self(
            'Set the engine name before setting the password as that will be hashed Engine specific',
            self::MODEL_ENGINE_SET_AFTER_PASSWORD,
            $previous
        );
    }
}
