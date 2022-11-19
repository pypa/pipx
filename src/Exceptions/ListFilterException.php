<?php

namespace Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class ListFilterException extends ClusterApiException
{
    public static function invalidModel(Throwable $previous = null): ListFilterException
    {
        return new self(
            'The provided model can\'t be use for a filter, the model must implement the `Model` contract',
            self::LISTFILTER_INVALID_MODEL,
            $previous
        );
    }

    public static function unableToDetermineFields(Throwable $previous = null): ListFilterException
    {
        return new self(
            'Unable to get the available fields for the model',
            self::LISTFILTER_UNABLE_TO_DETERMINE_FIELDS,
            $previous
        );
    }

    public static function invalidSortMethod(string $providedSortMethod, Throwable $previous = null): ListFilterException
    {
        return new self(
            sprintf('The sort method `%s` is not available, use ASC or DESC', $providedSortMethod),
            self::LISTFILTER_INVALID_SORT_METHOD,
            $previous
        );
    }

    public static function fieldNotAvailable(string $field, Throwable $previous = null): ListFilterException
    {
        return new self(
            sprintf('The field `%s` is not available in the model', $field),
            self::LISTFILTER_FIELD_NOT_AVAILABLE,
            $previous
        );
    }
}
