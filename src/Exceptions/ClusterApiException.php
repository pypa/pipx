<?php

namespace Cyberfusion\ClusterApi\Exceptions;

use Exception;

class ClusterApiException extends Exception
{
    protected const AUTHENTICATION_REQUIRED = 100;
    protected const AUTHENTICATION_FAILED = 101;
    protected const AUTHENTICATION_MISSING = 102;
    protected const AUTHENTICATION_CREDENTIALS_INVALID = 104;

    protected const REQUEST_FAILED = 200;
    protected const REQUEST_INVALID = 201;

    protected const API_NOT_UP = 300;

    protected const MODEL_PROPERTY_NOT_AVAILABLE = 400;

    protected const VALIDATION_FAILED = 500;

    protected const LISTFILTER_INVALID_SORT_METHOD = 600;
    protected const LISTFILTER_FIELD_NOT_AVAILABLE = 601;
    protected const LISTFILTER_INVALID_MODEL = 602;
    protected const LISTFILTER_UNABLE_TO_DETERMINE_FIELDS = 603;
    protected const LISTFILTER_INVALID_TYPE = 604;
    protected const LISTFILTER_INVALID_ARRAY_STRUCTURE = 605;
}
