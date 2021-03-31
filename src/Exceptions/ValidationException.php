<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class ValidationException extends ClusterApiException
{
    public static function validationFailed(array $failedValidations = [], Throwable $previous = null): ValidationException
    {
        return new self(
            sprintf('The validation failed: `%s`', implode(', ', $failedValidations)),
            self::VALIDATION_FAILED,
            $previous
        );
    }
}
