<?php

namespace Cyberfusion\ClusterApi\Endpoints;

use Cyberfusion\ClusterApi\Exceptions\RequestException;
use Cyberfusion\ClusterApi\Models\Daemon;
use Cyberfusion\ClusterApi\Request;
use Cyberfusion\ClusterApi\Response;
use Cyberfusion\ClusterApi\Support\ListFilter;

class Daemons extends Endpoint
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
      ->setUrl(sprintf('daemons?%s', $filter->toQuery()));

    $response = $this
      ->client
      ->request($request);
    if (!$response->isSuccess()) {
      return $response;
    }

    return $response->setData([
      'daemons' => array_map(
        fn (array $data) => (new Daemon())->fromArray($data),
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
      ->setUrl(sprintf('daemons/%d', $id));

    $response = $this
      ->client
      ->request($request);
    if (!$response->isSuccess()) {
      return $response;
    }

    return $response->setData([
      'daemon' => (new Daemon())->fromArray($response->getData()),
    ]);
  }

  /**
   * @throws RequestException
   */
  public function create(Daemon $daemon): Response
  {
    $this->validateRequired($daemon, 'create', [
      'name',
      'command',
      'nodes_ids',
      'unix_user_id',
    ]);

    $request = (new Request())
      ->setMethod(Request::METHOD_POST)
      ->setUrl('daemons')
      ->setBody(
        $this->filterFields($daemon->toArray(), [
          'name',
          'command',
          'unix_user_id',
          'nodes_ids',
        ])
      );

    $response = $this
      ->client
      ->request($request);
    if (!$response->isSuccess()) {
      return $response;
    }

    $daemon = (new Daemon())->fromArray($response->getData());

    return $response->setData([
      'daemon' => $daemon,
    ]);
  }

  /**
   * @throws RequestException
   */
  public function update(Daemon $daemon): Response
  {
    $this->validateRequired($daemon, 'update', [
      'name',
      'command',
      'unix_user_id',
      'nodes_ids',
      'cluster_id',
      'id',
    ]);

    $request = (new Request())
      ->setMethod(Request::METHOD_PUT)
      ->setUrl(sprintf('daemons/%d', $daemon->getId()))
      ->setBody(
        $this->filterFields($daemon->toArray(), [
          'name',
          'command',
          'unix_user_id',
          'nodes_ids',
          'node_id',
          'id',
        ])
      );

    $response = $this
      ->client
      ->request($request);
    if (!$response->isSuccess()) {
      return $response;
    }

    $daemon = (new Daemon())->fromArray($response->getData());

    return $response->setData([
      'daemon' => $daemon,
    ]);
  }

  /**
   * @throws RequestException
   */
  public function delete(int $id): Response
  {
    $request = (new Request())
      ->setMethod(Request::METHOD_DELETE)
      ->setUrl(sprintf('daemons/%d', $id));

    return $this
      ->client
      ->request($request);
  }
}
