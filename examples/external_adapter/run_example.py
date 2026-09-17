"""Run after installing REE. Registration uses explicit trusted Python."""
import argparse
from pathlib import Path

from adapter import SOURCE, FixtureAdapter

from ree.config import ProjectConfig
from ree.pipeline import run

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=Path('outputs'))
args = parser.parse_args()
config = ProjectConfig(project={'name': 'synthetic-adapter'}, mode='live', topics=['earthquake'],
                       collection={'public_sources': True, 'sources': [SOURCE['id']]}, export_policy='public')
root, manifest = run(config, live=True, output=args.output,
                     adapters={SOURCE['id']: FixtureAdapter}, source_registry=[SOURCE])
print(f"Synthetic extension: {manifest['status']}; {root}")
