"""MeitouClient adapter 0.14.1 save_roots: the runner reads a save's identities from the root that holds it."""
from oracle_runner import OracleSession


def _save(root, name):
    folder = root / name
    folder.mkdir(parents=True)
    (folder / 'quick.save').write_bytes(b'')


def test_the_first_root_holding_the_save_wins_and_save_root_stays_the_fallback(tmp_path):
    meitou, kenshi = tmp_path / 'Meitou' / 'save', tmp_path / 'kenshi' / 'save'
    _save(meitou, 'arena')
    _save(kenshi, 'arena')
    _save(kenshi, 'town')
    session = OracleSession(dict(target='meitou'))
    status = dict(save_root=str(kenshi), save_roots=[str(meitou), str(kenshi)])
    assert session.source_root(status, 'arena') == meitou
    assert session.source_root(status, 'town') == kenshi
    assert session.source_root(status, 'missing') == meitou
    assert session.source_root(dict(save_root=str(kenshi)), 'arena') == kenshi
    assert session.source_root(status) == kenshi
