<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Exceptions;

use Exception;

class ClusterApiException extends Exception
{
    protected const AUTHENTICATION_REQUIRED = 100;
    protected const AUTHENTICATION_FAILED = 101;
    protected const AUTHENTICATION_MISSING = 102;
    protected const AUTHENTICATION_CREDENTIALS_INVALID = 104;

    protected const REQUEST_FAILED = 200;
    protected const REQUEST_INVALID = 201;
}
