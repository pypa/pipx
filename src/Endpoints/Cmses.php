<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\Cms;
use Vdhicts\Cyberfusion\ClusterApi\Models\CmsInstallation;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class Cmses extends Endpoint
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
            ->setUrl(sprintf('cmses?%s', $filter->toQuery()));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cmses' => array_map(
                function (array $data) {
                    return (new Cms())->fromArray($data);
                },
                $response->getData()
            ),
        ]);
    }

    /**
     * @param int $id
     * @param bool $oneTimeLoginUrl
     * @return Response
     * @throws RequestException
     */
    public function get(int $id, bool $oneTimeLoginUrl = false): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_GET)
            ->setUrl(sprintf(
                'cmses/%d?%s',
                $id,
                http_build_query(['get_one_time_login_url' => $oneTimeLoginUrl])
            ));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'cms' => (new Cms())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param Cms $cms
     * @return Response
     * @throws RequestException
     */
    public function create(Cms $cms): Response
    {
        $this->validateRequired($cms, 'create', [
            'software_name',
            'virtual_host_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('cmses')
            ->setBody($this->filterFields($cms->toArray(), [
                'software_name',
                'is_manually_created',
                'virtual_host_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cms = (new Cms())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($cms->getClusterId());

        return $response->setData([
            'cms' => $cms,
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
                ->getData('cms')
                ->getClusterId();

            $this
                ->client
                ->addAffectedCluster($clusterId);
        }

        $request = (new Request())
            ->setMethod(Request::METHOD_DELETE)
            ->setUrl(sprintf('cmses/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @param int $id
     * @param CmsInstallation $cmsInstallation
     * @return Response
     * @throws RequestException
     */
    public function install(int $id, CmsInstallation $cmsInstallation): Response
    {
        $this->validateRequired($cmsInstallation, 'create', [
            'database_name',
            'database_user_name',
            'database_user_password',
            'database_host',
            'site_title',
            'site_url',
            'locale',
            'version',
            'admin_username',
            'admin_password',
            'admin_email_address',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('cmses/%d/install', $id))
            ->setBody($this->filterFields($cmsInstallation->toArray(), [
                'database_name',
                'database_user_name',
                'database_user_password',
                'database_host',
                'site_title',
                'site_url',
                'locale',
                'version',
                'admin_username',
                'admin_password',
                'admin_email_address',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (!$response->isSuccess()) {
            return $response;
        }

        $cms = (new Cms())->fromArray($response->getData());

        // Log which cluster is affected by this change
        $this
            ->client
            ->addAffectedCluster($cms->getClusterId());

        return $response->setData([
            'cms' => $cms,
        ]);
    }
}
