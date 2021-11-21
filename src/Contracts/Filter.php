<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Contracts;

interface Filter
{
    public function toQuery(): string;
}
