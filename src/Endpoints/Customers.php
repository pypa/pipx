<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Customer;
use Cyberfusion\ClusterApi\Models\HostIpAddress;
use Cyberfusion\ClusterApi\Models\IpAddressCreate;
use Cyberfusion\ClusterApi\Models\IpAddressProduct;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class Customers extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if (!$filter instanceof ListFilter) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('customers?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customers' => array_map(
                fn (array $data) => (new Customer())->fromArray($data),
                $response->getData()
            ),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function get(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('customers/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'customer' => (new Customer())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
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

    /**
     * @throws RequestException
     */
    public function createIpAddress(int $customerId, IpAddressCreate $customerIpAddress): Response
    {
        $this->validateRequired($customerIpAddress, 'create', [
            'service_account_name',
            'dns_name',
            'address_family',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('customers/%d/ip-addresses', $customerId))
            ->setBody(
                $this->filterFields($customerIpAddress->toArray(), [
                    'service_account_name',
                    'dns_name',
                    'address_family',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'taskCollection' => (new TaskCollection())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function deleteIpAddress(int $customerId, int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('customers/%d/ip-addresses/%d', $customerId, $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function products(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl('nodes-add-ons/products');

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'ipAddressProducts' => array_map(
                fn (array $data) => (new IpAddressProduct())->fromArray($data),
                $response->getData()
            ),
        ]);
    }
}
