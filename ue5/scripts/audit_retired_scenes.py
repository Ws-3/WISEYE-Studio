"""Read-only registry audit before removing the two retired WISEYE maps.

Run as a Python commandlet in the derived project. Never loads/saves a world.
"""
import json
from pathlib import Path
import unreal

registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(
    include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=False, include_soft_management_references=False,
    include_hard_management_references=False)
prefixes = ('/Game/WISEYE-test', '/Game/WISEYE/Scenes/test_range',
            '/Game/__ExternalActors__/WISEYE-test', '/Game/__ExternalObjects__/WISEYE-test',
            '/Game/__ExternalActors__/WISEYE/Scenes/test_range',
            '/Game/__ExternalObjects__/WISEYE/Scenes/test_range')
def retired(package):
    return any(package == p or package.startswith(p + '/') for p in prefixes)
packages = sorted({str(a.package_name) for a in registry.get_all_assets() if retired(str(a.package_name))})
outside = {}
for package in packages:
    references = sorted(str(p) for p in registry.get_referencers(package, options) if not retired(str(p)))
    if references:
        outside[package] = references
result = dict(packages=packages, outside_referencers=outside,
              small_city_registered=bool(registry.get_assets_by_package_name('/Game/WISEYE/Scenes/city/CitySample')),
              big_city_registered=bool(registry.get_assets_by_package_name('/Game/Map/Big_City_LVL')))
out = Path(unreal.Paths.project_dir()) / 'Saved/retired-scenes-audit.json'
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
unreal.log('WISEYE retired scene audit: ' + str(out) + ' external references=' + str(len(outside)))
