"""Exact bounded assets are evidence inputs, never text witnesses or playback PASS."""
from hashlib import sha256
from io import BytesIO
import json
import subprocess
from types import SimpleNamespace
import wave

import pytest

from spg.domain.model_runtime import ModelUsage
from spg.providers.static_web_audio import audio_observation
from spg.providers.protected_context_verifier import StaticProtectedContextVerifier
from tests.test_static_protected_context_verifier import subject, check  # noqa: F401


def wav():
    out = BytesIO()
    with wave.open(out, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000)
        f.writeframes(b'\x01\x00' * 800)
    return out.getvalue()


def test_audio_format_observations_do_not_claim_playback_or_quality():
    assert audio_observation(wav(), '.wav') == {'format': 'PCM_WAVE', 'sample_rate': 8000, 'channels': 1, 'sample_width': 2, 'frames': 800}
    # Format framing fixture only; it does not claim to be audible music.
    frame = bytes.fromhex('fffb9000') + b'\0' * 413
    assert audio_observation(frame * 2, '.mp3')['observed_consecutive_frames'] == 2
    with pytest.raises(ValueError, match='AUDIO_INVALID'): audio_observation(frame, '.mp3')
    with pytest.raises(ValueError, match='AUDIO_INVALID'): audio_observation(wav()[:-3], '.wav')


@pytest.mark.parametrize('body', [b'', b'<html>not an audio file</html>', b'ID3\4\0\0\0\0\0\0', b'\xff\xfb\x90\0'])
def test_labels_and_incidental_headers_are_not_valid_local_audio(body):
    with pytest.raises(ValueError, match='AUDIO_INVALID'): audio_observation(body, '.mp3')


@pytest.mark.parametrize('kind', ['valid', 'invalid', 'symlink', 'oversized'])
def test_exact_candidate_reads_bounded_audio_before_model_and_persists_identity(subject, kind):
    repo, base, request, task, contract = subject
    asset = repo / 'music.wav'
    if kind == 'symlink': asset.symlink_to('index.html')
    else: asset.write_bytes(wav() if kind == 'valid' else b'x' * 8000001 if kind == 'oversized' else b'not music')
    (repo / 'index.html').write_text('<main>Company Home</main><audio src="music.wav" loop controls></audio>')
    def git(*args): return subprocess.check_output(['git','-C',str(repo),*args]).decode().strip()
    git('add','.'); git('commit','-m','Candidate with exact audio')
    request = request.model_copy(update={'proposed_commit_identity': git('rev-parse','HEAD'), 'tree_identity': git('rev-parse','HEAD^{tree}')})
    contract = SimpleNamespace(allowed_areas=(),exact_targets=(*contract.exact_targets,SimpleNamespace(path='music.wav')))
    calls = []
    def generate(**kw):
        calls.append(json.loads(kw['input_text']))
        return SimpleNamespace(output_text=json.dumps({'checks':[check()]}),provider=SimpleNamespace(value='fixture'),effective_model='fixture',request_id='fixture',usage=ModelUsage())
    verifier = StaticProtectedContextVerifier(lambda: SimpleNamespace(generate=generate,registry=SimpleNamespace(close=lambda:None)))
    if kind != 'valid':
        with pytest.raises(ValueError): verifier.verify(request,task,contract,repo,base)
        assert not calls
    else:
        checks = verifier.verify(request,task,contract,repo,base)
        assert 'music.wav' not in calls[0]['candidate_sources']
        assert calls[0]['candidate_assets']['music.wav']['sha256'] == sha256(wav()).hexdigest()
        assert checks[0]['observed_audio_assets'] == calls[0]['candidate_assets']
    assert not StaticProtectedContextVerifier.supports(SimpleNamespace(allowed_areas=(),exact_targets=(SimpleNamespace(path='music.wav'),)))
    assert not StaticProtectedContextVerifier.supports(SimpleNamespace(allowed_areas=(),exact_targets=(SimpleNamespace(path='index.html'),SimpleNamespace(path='server.py'))))
