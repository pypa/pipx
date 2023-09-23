<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\CertificateManager;
use Cyberfusion\ClusterApi\Models\TaskCollection;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class CertificateManagers extends Endpoint
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
            ->setUrl(sprintf('certificate-managers?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'certificateManagers' => array_map(
                fn (array $data) => (new CertificateManager())->fromArray($data),
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
            ->setUrl(sprintf('certificate-managers/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'certificateManager' => (new CertificateManager())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function create(CertificateManager $certificateManager): Response
    {
        $this->validateRequired($certificateManager, 'create', [
            'common_names',
            'provider_name',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('certificate-managers')
            ->setBody(
                $this->filterFields($certificateManager->toArray(), [
                    'common_names',
                    'provider_name',
                    'request_callback_url',
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
            'certificateManager' => (new CertificateManager())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function update(CertificateManager $certificateManager): Response
    {
        $this->validateRequired($certificateManager, 'update', [
            'common_names',
            'provider_name',
            'request_callback_url',
            'last_request_task_collection_uuid',
            'cluster_id',
            'id',
            'main_common_name',
            'certificate_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('certificate-managers/%d', $certificateManager->getId()))
            ->setBody(
                $this->filterFields($certificateManager->toArray(), [
                    'common_names',
                    'provider_name',
                    'request_callback_url',
                    'last_request_task_collection_uuid',
                    'cluster_id',
                    'id',
                    'main_common_name',
                    'certificate_id',
                ])
            );

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'certificateManager' => (new CertificateManager())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function restore(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('certificate-managers/%d/restore', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'certificateManager' => (new CertificateManager())->fromArray($response->getData()),
        ]);
    }

    /**
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('certificate-managers/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @throws RequestException
     */
    public function request(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('certificate-managers/%d/request', $id));

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
}
