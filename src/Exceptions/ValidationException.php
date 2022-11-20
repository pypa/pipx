<?php

namespace Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class ValidationException extends ClusterApiException
{
    public static function validationFailed(array $failedValidations = [], Throwable $previous = null): self
    {
        return new self(
            sprintf('The validation failed: `%s`', implode(', ', $failedValidations)),
            self::VALIDATION_FAILED,
            $previous
        );
    }
}
