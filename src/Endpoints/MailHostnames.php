<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\MailHostname;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class MailHostnames extends Endpoint
{
    /**
     * @param ListFilter|null $filter
     * @return Response
     * @throws RequestException
     */
    public function list(ListFilter $filter = null): Response
    {
        if (is_null($filter)) {
            $filter = new ListFilter();
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('mail-hostnames?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailHostnames' => array_map(
                function (array $data) {
                    return (new MailHostname())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function get(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf('mail-hostnames/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'mailHostname' => (new MailHostname())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param MailHostname $mailHostname
     * @return Response
     * @throws RequestException
     */
    public function create(MailHostname $mailHostname): Response
    {
        $this->validateRequired($mailHostname, 'create', [
            'domain',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('mail-hostnames')
            ->setBody($this->filterFields($mailHostname->toArray(), [
                'domain',
                'certificate_id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $mailHostname = (new MailHostname())->fromArray($response->getData());

        return $response->setData([
            'mailHostname' => $mailHostname,
        ]);
    }

    /**
     * @param MailHostname $mailHostname
     * @return Response
     * @throws RequestException
     */
    public function update(MailHostname $mailHostname): Response
    {
        $this->validateRequired($mailHostname, 'update', [
            'domain',
            'cluster_id',
            'id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('mail-hostnames/%d', $mailHostname->getId()))
            ->setBody($this->filterFields($mailHostname->toArray(), [
                'domain',
                'certificate_id',
                'cluster_id',
                'id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $mailHostname = (new MailHostname())->fromArray($response->getData());

        return $response->setData([
            'mailHostname' => $mailHostname,
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('mail-hostnames/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
