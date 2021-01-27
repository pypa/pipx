<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class ClientException extends ClusterApiException
{
    public static function authenticationMissing(Throwable $previous = null): ClientException
    {
        return new self(
            'Missing information to authenticate, please provide an access token or the credentials',
            self::AUTHENTICATION_MISSING,
            $previous
        );
    }

    public static function invalidCredentials(Throwable $previous = null): ClientException
    {
        return new self(
            'The provided credentials are invalid, please check the username and password',
            self::AUTHENTICATION_CREDENTIALS_INVALID,
            $previous
        );
    }

    public static function authenticationFailed(Throwable $previous = null): ClientException
    {
        return new self(
            'Failed to authenticate',
            self::AUTHENTICATION_FAILED,
            $previous
        );
    }

    public static function apiNotUp(Throwable $previous = null): ClientException
    {
        return new self(
            'The API is not available at this moment',
            self::API_NOT_UP,
            $previous
        );
    }
}
