<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\MailDomain;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class MailDomains extends Endpoint
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
            ->setUrl(sprintf('mail-domains?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailDomains' => array_map(
                fn(array $data) => (new MailDomain())->fromArray($data),
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
            ->setUrl(sprintf('mail-domains/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailDomain' => (new MailDomain())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(MailDomain $mailDomain): Response
    {
        $this->validateRequired($mailDomain, 'create', [
            'domain',
            'catch_all_forward_email_addresses',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mail-domains')
            ->setBody(
                $this->filterFields($mailDomain->toArray(), [
                    'domain',
                    'catch_all_forward_email_addresses',
                    'is_local',
                    'unix_user_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $mailDomain = (new MailDomain())->fromArray($response->getData());

        return $response->setData([
            'mailDomain' => $mailDomain,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(MailDomain $mailDomain): Response
    {
        $this->validateRequired($mailDomain, 'update', [
            'domain',
            'catch_all_forward_email_addresses',
            'unix_user_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('mail-domains/%d', $mailDomain->getId()))
            ->setBody(
                $this->filterFields($mailDomain->toArray(), [
                    'domain',
                    'catch_all_forward_email_addresses',
                    'is_local',
                    'unix_user_id',
                    'id',
                    'cluster_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $mailDomain = (new MailDomain())->fromArray($response->getData());

        return $response->setData([
            'mailDomain' => $mailDomain,
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('mail-domains/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
