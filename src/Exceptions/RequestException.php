<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class RequestException extends ClusterApiException
{
    public static function authenticationRequired(Throwable $previous = null): RequestException
    {
        return new self(
            'The request requires authentication, login before making this request',
            self::AUTHENTICATION_REQUIRED,
            $previous
        );
    }

    public static function requestFailed(string $message, Throwable $previous = null): RequestException
    {
        return new self(
            sprintf('Request failed, error: `%s`', $message),
            self::REQUEST_FAILED,
            $previous
        );
    }

    public static function invalidRequest(
        string $type,
        string $action,
        array $missing,
        Throwable $previous = null
    ): RequestException {
        return new self(
            sprintf(
                '%s %s request not possible, missing: `%s`',
                ucfirst($action),
                $type,
                implode(', ', $missing)
            ),
            self::REQUEST_INVALID,
            $previous
        );
    }
}
