<?php

namespace Cyberfusion\ClusterApi\Contracts;

interface Filter
{
    public function toQuery(): string;
}
