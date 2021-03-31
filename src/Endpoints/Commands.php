<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\Command;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;
use Vdhicts\Cyberfusion\ClusterApi\Support\ListFilter;

class Commands extends Endpoint
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
            ->setUrl(sprintf('commands?%s', http_build_query($filter->toArray())));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'commands' => array_map(
                function (array $data) {
                    return (new Command())->fromArray($data);
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
            ->setUrl(sprintf('commands/%d', $id));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'command' => (new Command())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param Command $command
     * @return Response
     * @throws RequestException
     */
    public function create(Command $command): Response
    {
        $this->validateRequired($command, 'create', [
            'command',
            'secret_values',
            'virtual_host_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('commands')
            ->setBody($this->filterFields($command->toArray(), [
                'command',
                'secret_values',
                'virtual_host_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'command' => (new Command())->fromArray($response->getData()),
        ]);
    }

    /**
     * @param Command $command
     * @return Response
     * @throws RequestException
     */
    public function update(Command $command): Response
    {
        $this->validateRequired($command, 'update', [
            'command',
            'secret_values',
            'virtual_host_id',
            'id',
            'cluster_id',
        ]);

        $request = (new Request())
            ->setMethod(Request::METHOD_PUT)
            ->setUrl(sprintf('commands/%d', $command->getId()))
            ->setBody($this->filterFields($command->toArray(), [
                'command',
                'secret_values',
                'virtual_host_id',
                'id',
                'cluster_id',
            ]));

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'command' => (new Command())->fromArray($response->getData()),
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
            ->setUrl(sprintf('commands/%d', $id));

        return $this
            ->client
            ->request($request);
    }

    /**
     * @param int $id
     * @return Response
     * @throws RequestException
     */
    public function run(int $id): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl(sprintf('commands/%d/run', $id));

        return $this
            ->client
            ->request($request);
    }
}
