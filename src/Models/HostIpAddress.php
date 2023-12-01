<?php

namespace Cyberfusion\ClusterApi\Models;

class HostIpAddress extends ClusterModel
{
    private string $name;
    /**
     * @var array<IpAddress>
     */
    private array $ipAddress = [];

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): self
    {
        $this->name = $name;

        return $this;
    }

    public function getIpAddress(): array
    {
        return $this->ipAddress;
    }

    public function setIpAddress(array $ipAddress = []): self
    {
        $this->ipAddress = $ipAddress;

        return $this;
    }

    public function fromArray(array $data): self
    {
        return $this
            ->setName(array_key_first($data))
            ->setIpAddress(
                array_map(
                    fn (array $ipAddress) => (new IpAddress())->fromArray($ipAddress),
                    $data[$this->getName()]
                )
            );
    }

    public function toArray(): array
    {
        return [
            $this->getName() => array_map(
                fn (IpAddress $ipAddress) => $ipAddress->toArray(),
                $this->getIpAddress()
            )
        ];
    }
}
