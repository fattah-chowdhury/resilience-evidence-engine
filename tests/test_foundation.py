import sqlite3

import pytest

from ree.cli import main
from ree.config import ProjectConfig, initialize, load_config
from ree.storage import connect, stable_id


def test_init_roundtrip(tmp_path):
    path = initialize(tmp_path / 'study')
    config = load_config(path)
    assert config.project.name == 'study'
    assert not config.collection.public_sources
    assert not config.processing.llm_enabled
    assert len(config.fingerprint()) == 64


def test_init_refuses_overwrite(tmp_path):
    path = initialize(tmp_path / 'study')
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        initialize(path.parent)
    assert path.read_bytes() == before


@pytest.mark.parametrize('data', [
    {}, {'project': {'name': '../unsafe'}},
    {'project': {'name': 'a'}, 'typo': True},
    {'project': {'name': 'a'}, 'time': {'start': '2026-02-01', 'end': '2026-01-01'}},
    {'project': {'name': 'a'}, 'exports': ['shapefile']},
    {'project': {'name': 'a'}, 'collection': {'max_records': 0}},
    {'project': {'name': 'a'}, 'topics': []},
    {'project': {'name': 'a'}, 'schema_version': 2},
])
def test_invalid_config(data):
    with pytest.raises(ValueError):
        ProjectConfig.model_validate(data)


@pytest.mark.parametrize('content', [
    'project: {name: a}\nproject: {name: b}',
    '!!python/object/apply:os.system [echo unsafe]', '[]',
])
def test_bad_yaml(tmp_path, content):
    path = tmp_path / 'bad.yml'
    path.write_text(content)
    assert main(['validate', '--config', str(path)]) == 2


def test_separate_entities_and_orphans():
    db = connect()
    try:
        names = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'source', 'document', 'claim', 'location', 'event', 'assessment', 'provenance'} <= names
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO claim(claim_id,document_id,statement) VALUES ('c','missing','test')")
        assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
    finally:
        db.close()


def test_ids_are_stable_unambiguous_and_namespaced():
    assert stable_id('claim', 'a') == stable_id('claim', 'a')
    assert stable_id('claim', 'a', 'bc') != stable_id('claim', 'ab', 'c')
    assert stable_id('claim', 'a') != stable_id('event', 'a')


def test_cli(tmp_path, capsys):
    assert main(['init', str(tmp_path / 'sample')]) == 0
    assert main(['validate', '--config', str(tmp_path / 'sample/project.yml')]) == 0
    assert main(['doctor']) == 0
    assert 'local checks only' in capsys.readouterr().out


def test_missing_config(tmp_path):
    assert main(['validate', '--config', str(tmp_path / 'missing')]) == 2
