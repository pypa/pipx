<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class IpAddressProduct extends ClusterModel
{
    private ?string $uuid = null;
    private ?string $name = null;
    private ?string $type = null;
    private int|float|null $price = null;
    private ?string $period = null;
    private ?string $currency = null;

    public function getUuid(): ?string
    {
        return $this->uuid;
    }

    public function setUuid(?string $uuid): self
    {
        Validator::value($uuid)
            ->uuid()
            ->nullable()
            ->validate();

        $this->uuid = $uuid;
        return $this;
    }

    public function getName(): ?string
    {
        return $this->name;
    }

    public function setName(?string $name): self
    {
        Validator::value($name)
            ->minLength(1)
            ->maxLength(64)
            ->pattern('^[a-zA-Z0-9 ]+$')
            ->nullable()
            ->validate();

        $this->name = $name;
        return $this;
    }

    public function getType(): ?string
    {
        return $this->type;
    }

    public function setType(?string $type): self
    {
        Validator::value($type)
            ->valuesIn(['outgoing', 'incoming'])
            ->nullable()
            ->validate();

        $this->type = $type;
        return $this;
    }

    public function getPrice(): float|int|null
    {
        return $this->price;
    }

    public function setPrice(float|int|null $price): self
    {
        Validator::value($price)
            ->maxAmount(0)
            ->nullable()
            ->validate();

        $this->price = $price;
        return $this;
    }

    public function getPeriod(): ?string
    {
        return $this->period;
    }

    public function setPeriod(?string $period): self
    {
        Validator::value($period)
            ->minLength(2)
            ->maxLength(2)
            ->pattern('^[A-Z0-9]+$')
            ->nullable()
            ->validate();

        $this->period = $period;
        return $this;
    }

    public function getCurrency(): ?string
    {
        return $this->currency;
    }

    public function setCurrency(?string $currency): self
    {
        Validator::value($currency)
            ->minLength(3)
            ->maxLength(3)
            ->pattern('^[A-Z]+$')
            ->nullable()
            ->validate();

        $this->currency = $currency;
        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setUuid(Arr::get($data, 'uuid'))
            ->setName(Arr::get($data, 'name'))
            ->setType(Arr::get($data, 'type'))
            ->setPrice(Arr::get($data, 'price'))
            ->setPeriod(Arr::get($data, 'period'))
            ->setCurrency(Arr::get($data, 'currency'));
    }

    public function toArray(): array
    {
        return [
            'uuid' => $this->uuid,
            'name' => $this->name,
            'type' => $this->type,
            'price' => $this->price,
            'period' => $this->period,
            'currency' => $this->currency,
        ];
    }
}
