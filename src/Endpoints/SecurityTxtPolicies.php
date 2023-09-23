<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\SecurityTxtPolicy;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class SecurityTxtPolicies extends Endpoint
{
    /**
     * @throws RequestException
     */
    public function list(?ListFilter $filter = null): Response
    {
        if (is_null($filter)) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('security-txt-policies?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'securityTxtPolicies' => array_map(
                fn (array $data) => (new SecurityTxtPolicy())->fromArray($data),
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
            ->setUrl(sprintf('security-txt-policies/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'securityTxtPolicy' => (new SecurityTxtPolicy())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(SecurityTxtPolicy $securityTxtPolicy): Response
    {
        $this->validateRequired($securityTxtPolicy, 'create', [
            'expires_timestamp',
            'email_contacts',
            'url_contacts',
            'encryption_key_urls',
            'acknowledgment_urls',
            'policy_urls',
            'opening_urls',
            'preferred_languages',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('security-txt-policies')
            ->setBody(
                $this->filterFields($securityTxtPolicy->toArray(), [
                    'expires_timestamp',
                    'email_contacts',
                    'url_contacts',
                    'encryption_key_urls',
                    'acknowledgment_urls',
                    'policy_urls',
                    'opening_urls',
                    'preferred_languages',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'securityTxtPolicy' => (new SecurityTxtPolicy())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(SecurityTxtPolicy $securityTxtPolicy): Response
    {
        $this->validateRequired($securityTxtPolicy, 'update', [
            'expires_timestamp',
            'email_contacts',
            'url_contacts',
            'encryption_key_urls',
            'acknowledgment_urls',
            'policy_urls',
            'opening_urls',
            'preferred_languages',
            'cluster_id',
            'id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('security-txt-policies/%d', $securityTxtPolicy->getId()))
            ->setBody(
                $this->filterFields($securityTxtPolicy->toArray(), [
                    'expires_timestamp',
                    'email_contacts',
                    'url_contacts',
                    'encryption_key_urls',
                    'acknowledgment_urls',
                    'policy_urls',
                    'opening_urls',
                    'preferred_languages',
                    'cluster_id',
                    'id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'securityTxtPolicy' => (new SecurityTxtPolicy())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('security-txt-policies/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
