<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Models;

use Illuminate\Support\Arr;
use Vdhicts\Cyberfusion\ClusterApi\Contracts\Model;

class DetailMessage implements Model
{
    public string $detail;

    public function fromArray(array $data): DetailMessage
    {
        $detailMessage = new self();
        $detailMessage->detail = Arr::get($data, 'detail', '');
        return $detailMessage;
    }

    public function toArray(): array
    {
        return [
            'detail' => $this->detail,
        ];
    }
}
