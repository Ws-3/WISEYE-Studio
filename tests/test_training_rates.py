import unittest
from training_client.rates import Rates


class RateTests(unittest.TestCase):
    def test_save_and_display_are_independent(self):
        rates=Rates(2,.5,True)
        self.assertEqual(rates.period(),.5)
        self.assertEqual(rates.due(0),(True,True))
        self.assertEqual(rates.due(.5),(True,False))
        self.assertEqual(rates.due(1),(True,False))
        self.assertEqual(rates.due(1.5),(True,False))
        self.assertEqual(rates.due(2),(True,True))

    def test_saving_can_run_faster_than_display_and_toggle_live(self):
        rates=Rates(.5,2,True)
        self.assertEqual(rates.due(0),(True,True))
        self.assertEqual(rates.due(.5),(False,True))
        rates.configure(.5,2,False)
        self.assertEqual(rates.period(),2)
        self.assertEqual(rates.due(1),(False,False))
        rates.configure(2,2,True)
        self.assertEqual(rates.due(1),(True,True))

    def test_no_backfill_or_duplicate_frames(self):
        rates=Rates(2,2,True);rates.due(0)
        self.assertEqual(rates.due(10),(True,True))
        self.assertEqual(rates.due(10),(False,False))
        for value in (0,11,float('nan'),True):
            with self.assertRaises(ValueError):rates.configure(value,1,True)

    def test_higher_display_and_save_rates_remain_independent(self):
        rates=Rates(5,10,True);self.assertAlmostEqual(rates.period(),.1)
        self.assertEqual(rates.due(0),(True,True));self.assertEqual(rates.due(.1),(False,True))
        self.assertEqual(rates.due(.2),(True,True))

    def test_preview_driven_source_does_not_drop_jittered_fresh_arrivals(self):
        rates=Rates(5,1,True)
        self.assertEqual(rates.due(0,source_driven=True),(True,True))
        self.assertEqual(rates.due(.19,source_driven=True),(True,False))
        self.assertEqual(rates.due(.19,source_driven=True),(False,False))
        self.assertEqual(rates.due(.41,source_driven=True),(True,False))
