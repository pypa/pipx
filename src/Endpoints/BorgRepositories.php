<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\BorgRepository;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class BorgRepositories extends Endpoint
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
            ->setUrl(sprintf('borg-repositories?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepositories' => array_map(
                function (array $data) {
                    return (new BorgRepository())->fromArray($data);
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
            ->setUrl(sprintf('borg-repositories/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepository' => (new BorgRepository())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param BorgRepository $borgRepository
     * @return Response
     * @throws RequestException
     */
    public function create(BorgRepository $borgRepository): Response
    {
        $this->validateRequired($borgRepository, 'create', [
            'name',
            'passphrase',
            'keep_hourly',
            'keep_daily',
            'keep_weekly',
            'keep_monthly',
            'keep_yearly',
            'unix_user_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('borg-repositories')
            ->setBody($this->filterFields($borgRepository->toArray(), [
                'name',
                'passphrase',
                'keep_hourly',
                'keep_daily',
                'keep_weekly',
                'keep_monthly',
                'keep_yearly',
                'unix_user_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'borgRepository' => (new BorgRepository())->fromArray($response->getData()),
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
            ->setUrl(sprintf('borg-repositories/%d', $id));

        return $this
            ->client
            ->request($request);
    }
}
