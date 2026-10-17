"""Exact audio bytes remain accessible through both existing preview owners."""
from types import SimpleNamespace
from uuid import uuid4
import subprocess
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from spg.application.delivery import DeliveryApplicationService, artifact_media_type, read_artifact
from spg.application.preview_security import MAX_STATIC_AUDIO_BYTES
from spg.domain.product import ProductInvariantViolation, ProductRecordNotFound
from spg.infrastructure.candidate_preview_runtime import DockerCandidatePreviewRuntime


@pytest.mark.parametrize('suffix,mime', [('.mp3', 'audio/mpeg'), ('.wav', 'audio/wav')])
def test_exact_candidate_audio_uses_same_bytes_mime_and_staleness_boundary(tmp_path, suffix, mime):
    repo = tmp_path / 'repo'; repo.mkdir()
    def git(*args): return subprocess.check_output(['git','-C',str(repo),*args]).decode().strip()
    git('init','-b','main'); git('config','user.name','Preview'); git('config','user.email','preview@example.invalid')
    (repo/'index.html').write_text('<audio loop controls src="music' + suffix + '"></audio>')
    # Transport fixture, not a claim of format verification or audible quality.
    path = 'music' + suffix; body = b'bounded audio bytes' * 70000
    (repo/path).write_bytes(body); (repo/'secret.env').write_text('not previewable')
    (repo/'escape.mp3').symlink_to('index.html')
    git('add','.'); git('commit','-m','Exact preview subject')
    revision, tree = git('rev-parse','HEAD'), git('rev-parse','HEAD^{tree}')
    context = {'candidate_fingerprint':'exact','paths':['index.html',path,'escape.mp3','secret.env'],
        'repository_path':str(repo),'repository_revision':revision}
    service = SimpleNamespace(candidate_context=lambda _:context)
    assert DeliveryApplicationService.candidate_artifact(service, uuid4(), 'exact', path) == body
    assert artifact_media_type(path) == mime
    with pytest.raises(ProductInvariantViolation): DeliveryApplicationService.candidate_artifact(service,uuid4(),'stale',path)
    with pytest.raises(ProductRecordNotFound): DeliveryApplicationService.candidate_artifact(service,uuid4(),'exact','outside.mp3')
    with pytest.raises(ProductRecordNotFound): DeliveryApplicationService.candidate_artifact(service,uuid4(),'exact','secret.env')
    with pytest.raises(ProductInvariantViolation): read_artifact(str(repo),revision,'escape.mp3',software=True)
    runtime = DockerCandidatePreviewRuntime(tmp_path / 'previews')
    runtime._workspace = lambda _: repo
    preview_id = uuid4()
    started = runtime._static_start(preview_id, revision, tree)
    try:
        with urlopen(started['endpoint'] + path, timeout=5) as response:
            assert response.read() == body and response.headers['Content-Type'] == mime
            assert response.headers['X-Candidate-Revision'] == revision
            assert response.headers['X-Candidate-Tree'] == tree
        with pytest.raises(HTTPError): urlopen(started['endpoint'] + 'secret.env', timeout=5)
        with pytest.raises(HTTPError): urlopen(started['endpoint'] + 'escape.mp3', timeout=5)
    finally:
        runtime._static_servers[preview_id].shutdown(); runtime._static_servers[preview_id].server_close()
    (repo/path).write_bytes(b'x' * (MAX_STATIC_AUDIO_BYTES + 1))
    (repo/'large.txt').write_bytes(b'x' * 1048577)
    git('add','.'); git('commit','-m','Oversized files stay bounded')
    for rejected in (path, 'large.txt'):
        with pytest.raises(ProductInvariantViolation): read_artifact(str(repo),git('rev-parse','HEAD'),rejected,software=True)
