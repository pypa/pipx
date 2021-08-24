<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\Certificate;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class Certificates extends Endpoint
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
            ->setUrl(sprintf('certificates?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'certificates' => array_map(
                function (array $data) {
                    return (new Certificate())->fromArray($data);
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
            ->setUrl(sprintf('certificates/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'certificate' => (new Certificate())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param Certificate $certificate
     * @return Response
     * @throws RequestException
     */
    public function create(Certificate $certificate): Response
    {
        $requiredAttributes = is_null($certificate->getCertificate())
            ? ['common_names', 'cluster_id'] // Request Let's Encrypt certificate
            : ['certificate', 'ca_chain', 'private_key', 'cluster_id']; // Supply own certificate
        $this->validateRequired($certificate, 'create', $requiredAttributes);

        $isLetEnscrypt = $certificate->isLetsEncrypt();

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('certificates')
            ->setBody($this->filterFields($certificate->toArray(), [
                'common_names',
                'certificate',
                'ca_chain',
                'private_key',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $certificate = (new Certificate())->fromArray($response->getData());

        // Log which cluster is affected by this change
        if (!$isLetEnscrypt) {
            $this
                ->client
                ->addAffectedCluster($certificate->getClusterId());
        }

        return $response->setData([
            'certificate' => $certificate,
        ]);
    }

    /**
     * @param Certificate $certificate
     * @return Response
     * @throws RequestException
     */
    public function update(Certificate $certificate): Response
    {
        $this->validateRequired($certificate, 'update', ['id', 'cluster_id', 'main_common_name']);

        $request = (new Request())
            ->setMethod(Request::METHOD_PATCH)
            ->setUrl(sprintf('certificates/%d', $certificate->getId()))
            ->setBody($this->filterFields($certificate->toArray(), [
                'main_common_name',
                'common_names',
                'certificate',
                'ca_chain',
                'private_key',
                'status_message', // Can only be changed with the proper right
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $certificate = (new Certificate())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($certificate->getClusterId());

        return $response->setData([
            'certificate' => $certificate,
        ]);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function delete(int $id): Response
    {
        // Log the affected cluster by retrieving the model first
        $result = $this->get($id);
        if ($result->isSuccess()) {
            $clusterId = $result
                ->getData('certificate')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('certificates/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
