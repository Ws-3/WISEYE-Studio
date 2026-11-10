"""Read-only audit of active UE resources, excluding generated build archives."""
import argparse
import json
import os
from pathlib import Path


def audit(repository):
    repository = Path(repository).resolve()
    project = repository / 'ue5/WISEYE'
    links = []
    blocking = []
    for directory, dirs, files in os.walk(project, followlinks=False):
        dirs[:] = [n for n in dirs if n not in {'Binaries', 'Intermediate', 'Saved', 'DerivedDataCache', '.git'}]
        for name in dirs[:]:
            path = Path(directory) / name
            if path.is_junction() or path.is_symlink():
                target = path.resolve()
                item = {'path': str(path.relative_to(repository)), 'target': str(target), 'exists': target.exists()}
                item['kind'] = 'project-local' if target.is_relative_to(repository) else 'external-scene-assets' if 'CitySample' in target.parts else 'external-dependency'
                links.append(item)
                if not item['exists'] or item['kind'] == 'external-dependency':
                    blocking.append(item)
                dirs.remove(name)
    for name in ['ProjectAirSim', 'Drone']:
        content = project / 'Plugins' / name / 'Content'
        if not content.is_dir() or not content.resolve().is_relative_to(repository):
            blocking.append({'path': str(content), 'reason': 'Required plugin content must resolve inside this repository'})
    return {'project': str(project), 'links': links, 'blocking': blocking,
            'canonical_runtime_dependencies_local': not blocking,
            'note': 'City Sample is an optional external source-scene dependency; packaged runtime and custom-host SDK have different dependency contracts.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.repository)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'links': len(report['links']), 'blocking': report['blocking'],
                      'passed': report['canonical_runtime_dependencies_local']}, indent=2))
    raise SystemExit(0 if not report['blocking'] else 1)
