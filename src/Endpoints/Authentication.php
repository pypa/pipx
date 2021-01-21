<?php

namespace Vdhicts\Cyberfusion\ClusterApi\Endpoints;

use Vdhicts\Cyberfusion\ClusterApi\Exceptions\RequestException;
use Vdhicts\Cyberfusion\ClusterApi\Models\Login;
use Vdhicts\Cyberfusion\ClusterApi\Models\Token;
use Vdhicts\Cyberfusion\ClusterApi\Models\UserInfo;
use Vdhicts\Cyberfusion\ClusterApi\Request;
use Vdhicts\Cyberfusion\ClusterApi\Response;

class Authentication extends Endpoint
{
    /**
     * @param Login $login
     * @return Response
     * @throws RequestException
     */
    public function login(Login $login): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('login/access-token')
            ->setBody($this->filterFields($login->toArray()))
            ->setAuthenticationRequired(false);

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'token' => (new Token())->fromArray($response->getData()),
        ]);
    }

    /**
     * @return Response
     * @throws RequestException
     */
    public function verify(): Response
    {
        $request = (new Request())
            ->setMethod(Request::METHOD_POST)
            ->setUrl('login/test-token');

        $response = $this
            ->client
            ->request($request);
        if (! $response->isSuccess()) {
            return $response;
        }

        return $response->setData([
            'userInfo' => (new UserInfo())->fromArray($response->getData()),
        ]);
    }
}
