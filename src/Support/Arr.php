<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Support;

class Arr extends \Illuminate\Support\Arr
{
    /**
     * Removes the value from the array.
     *
     * @param array $array
     * @param mixed $value
     * @return array
     */
    public static function exceptValue(array $array, $value): array
    {
        if (!in_array($value, $array)) {
            return $array;
        }

        unset($array[$value]);

        return $array;
    }
}
