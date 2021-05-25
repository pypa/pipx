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
        $key = array_search($value, $array);
        if ($key === false) {
            return $array;
        }

        unset($array[$value]);

        return $array;
    }
}
