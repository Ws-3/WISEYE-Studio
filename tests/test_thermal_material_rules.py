import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ue5/scripts'))
from thermal_material_rules import classify,validated_rules

RULES = json.loads((Path(__file__).resolve().parents[1] / 'ue5/WISEYE/Config/WISEYE/thermal_material_classes.json').read_text(encoding='utf8'))['classes']


class ThermalMaterialRulesTests(unittest.TestCase):
    def test_config_cannot_use_target_ids_or_invalid_signals(self):
        import copy
        for field,value in [('id',97),('day_signal',float('nan')),('night_signal',True),('night_signal',2)]:
            broken=copy.deepcopy(RULES);broken[0][field]=value
            with self.assertRaises(ValueError):validated_rules({'classes':broken})
        self.assertEqual(len(validated_rules({'classes':RULES})),6)
    def test_mixed_glass_and_wall_cannot_label_entire_mesh(self):
        self.assertEqual(classify('SM_ConcreteBuilding', ['M_Glass', 'M_Concrete'], RULES)[0], 0)
        self.assertEqual(classify('SM_ConcreteBuilding', ['M_Glass', 'M_Generic'], RULES)[0], 0)

    def test_tree_parts_share_a_class_but_street_is_not_tree(self):
        self.assertEqual(classify('SM_Tree', ['MI_Leaf', 'MI_Bark'], RULES)[0], 4)
        self.assertEqual(classify('SM_StreetLight', ['M_Generic'], RULES)[0], 0)

    def test_mesh_fallback_does_not_override_conflicting_materials(self):
        self.assertEqual(classify('/Game/X/SM_Asphalt.SM_Asphalt', ['M_Generic'], RULES)[0], 1)
        self.assertEqual(classify('SM_Asphalt', ['M_Glass', 'M_Metal'], RULES)[0], 0)
