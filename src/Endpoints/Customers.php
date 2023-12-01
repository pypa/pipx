<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Models\HostIpAddress;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;

class Customers extends Endpoint
{
    public function ipAddresses(int $customerId): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('customers/%d/ip-addresses', $customerId));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $ipAddresses = [];
        foreach ($response->getData() as $name => $data) {
            $ipAddresses[$name] = (new HostIpAddress())->fromArray($data);
        }

        return $response->setData([
            'ipAddresses' => $ipAddresses,
        ]);
    }
}
