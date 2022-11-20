<?php

namespace Cyberfusion\ClusterApi\Exceptions;

use Throwable;

class ListFilterException extends ClusterApiException
{
    public static function invalidSortMethod(string $providedSortMethod, Throwable $previous = null): self
    {
        return new self(
            sprintf('The sort method `%s` is not available, use ASC or DESC', $providedSortMethod),
            self::LISTFILTER_INVALID_SORT_METHOD,
            $previous
        );
    }

    public static function fieldNotAvailable(string $field, Throwable $previous = null): self
    {
        return new self(
            sprintf('The `%s` is not available in the model', $field),
            self::LISTFILTER_FIELD_NOT_AVAILABLE,
            $previous
        );
    }
}
