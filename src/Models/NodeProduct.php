<?php

namespace Cyberfusion\ClusterApi\Models;

use Cyberfusion\ClusterApi\Support\Arr;
use Cyberfusion\ClusterApi\Support\Validator;

class NodeProduct extends ClusterModel
{
    private ?string $uuid = null;
    private ?string $name = null;
    private ?int $ram = null;
    private ?int $cores = null;
    private ?int $disk = null;
    private array $allowUpgradeTo = [];
    private array $allowDowngradeTo = [];
    private int|float|null $price = null;
    private ?string $period = null;
    private ?string $currency = null;

    public function getUuid(): string
    {
        return $this->uuid;
    }

    public function setUuid(?string $uuid): self
    {
        Validator::value($uuid)
            ->uuid()
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
            ->maxLength(2)
            ->pattern('^[A-Z]+$')
            ->nullable()
            ->validate();

        $this->name = $name;
        return $this;
    }

    public function getRam(): ?int
    {
        return $this->ram;
    }

    public function setRam(?int $ram): self
    {
        Validator::value($ram)
            ->minAmount(1)
            ->nullable()
            ->validate();

        $this->ram = $ram;
        return $this;
    }

    public function getCores(): ?int
    {
        return $this->cores;
    }

    public function setCores(?int $cores): self
    {
        Validator::value($cores)
            ->minAmount(1)
            ->nullable()
            ->validate();

        $this->cores = $cores;
        return $this;
    }

    public function getDisk(): ?int
    {
        return $this->disk;
    }

    public function setDisk(?int $disk): self
    {
        Validator::value($disk)
            ->minAmount(1)
            ->nullable()
            ->validate();

        $this->disk = $disk;
        return $this;
    }

    public function getAllowUpgradeTo(): array
    {
        return $this->allowUpgradeTo;
    }

    public function setAllowUpgradeTo(array $allowUpgradeTo = []): self
    {
        Validator::value($allowUpgradeTo)
            ->minLength(1)
            ->maxLength(2)
            ->pattern('^[A-Z]+$')
            ->each()
            ->validate();

        $this->allowUpgradeTo = $allowUpgradeTo;
        return $this;
    }

    public function getAllowDowngradeTo(): array
    {
        return $this->allowDowngradeTo;
    }

    public function setAllowDowngradeTo(array $allowDowngradeTo = []): self
    {
        Validator::value($allowDowngradeTo)
            ->minLength(1)
            ->maxLength(2)
            ->pattern('^[A-Z]+$')
            ->each()
            ->validate();

        $this->allowDowngradeTo = $allowDowngradeTo;
        return $this;
    }

    public function getPrice(): int|float|null
    {
        return $this->price;
    }

    public function setPrice(int|float|null $price): self
    {
        Validator::value($price)
            ->minAmount(0)
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
            ->pattern('^[A-Z]+$')
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
            ->setRam(Arr::get($data, 'ram'))
            ->setCores(Arr::get($data, 'cores'))
            ->setDisk(Arr::get($data, 'disk'))
            ->setAllowUpgradeTo(Arr::get($data, 'allow_upgrade_to', []))
            ->setAllowDowngradeTo(Arr::get($data, 'allow_downgrade_to', []))
            ->setPrice(Arr::get($data, 'price'))
            ->setPeriod(Arr::get($data, 'period'))
            ->setCurrency(Arr::get($data, 'currency'));
    }

    public function toArray(): array
    {
        return [
            'uuid' => $this->getUuid(),
            'name' => $this->getName(),
            'ram' => $this->getRam(),
            'cores' => $this->getCores(),
            'disk' => $this->getDisk(),
            'allow_upgrade_to' => $this->getAllowUpgradeTo(),
            'allow_downgrade_to' => $this->getAllowDowngradeTo(),
            'price' => $this->getPrice(),
            'period' => $this->getPeriod(),
            'currency' => $this->getCurrency(),
        ];
    }
}
