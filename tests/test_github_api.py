from unittest import mock

import pytest

from edp.utils import github


def test_no_token():
    api = github.GithubApi()
    assert 'User-Agent' in api._session.headers
    assert 'Authorization' not in api._session.headers


def test_with_token():
    api = github.GithubApi('foo')

    assert 'User-Agent' in api._session.headers
    assert 'Authorization' in api._session.headers


@pytest.fixture()
def api():
    with mock.patch('requests.Session') as session_mock:
        yield github.GithubApi()


# TODO: I dont like these tests

@pytest.mark.parametrize('owner', ['test_owner'])
@pytest.mark.parametrize('repo', ['test_repo'])
def test_get_releases(owner, repo, api):
    api.get_releases(owner, repo)
    assert owner in str(api._session.get.call_args[0])
    assert repo in str(api._session.get.call_args[0])


@pytest.mark.parametrize('owner', ['test_owner'])
@pytest.mark.parametrize('repo', ['test_repo'])
def test_get_releases_latest(owner, repo, api):
    api.get_releases_latest(owner, repo)
    assert owner in str(api._session.get.call_args[0])
    assert repo in str(api._session.get.call_args[0])


def test_create_release(api):
    api.create_release('test_owner', 'test_repo', 'test_tag', 'test_name', 'test_body')

    assert 'test_owner' in str(api._session.post.call_args[0])
    assert 'test_repo' in str(api._session.post.call_args[0])
    data = api._session.post.call_args[1]['json']
    assert 'test_tag' == data['tag_name']
    assert 'test_name' == data['name']
    assert 'test_body' == data['body']


@pytest.mark.parametrize('label', ['test', None])
def test_upload_asset(api, tempdir, label):
    filename = tempdir / 'foo'
    filename.write_text('test')

    api.upload_asset('test_url', filename, 'test_content_type', 'test_name', label=label)

    args = api._session.post.call_args[0]
    kwargs = api._session.post.call_args[1]

    assert args[0] == 'test_url'

    # with filename.open('r') as f:
    #     assert os.path.sameopenfile(f, api._session.post.call_args[1]['data'])

    if label is not None:
        assert 'label' in kwargs['params']
        assert kwargs['params']['label'] == label
    else:
        assert 'label' not in kwargs['params']

    assert 'test_content_type' == kwargs['headers']['Content-Type']
