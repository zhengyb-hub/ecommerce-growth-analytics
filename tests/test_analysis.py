import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_analysis import complete_months, feasible_mde, sample_size_two_proportions  # noqa: E402


class GrowthAnalysisTests(unittest.TestCase):
    data_dir = Path(__file__).resolve().parents[1] / "data" / "processed"

    def test_excludes_partial_final_month(self):
        monthly = pd.DataFrame({"order_month": pd.to_datetime(["2011-10-01", "2011-11-01", "2011-12-01"]), "revenue": [1, 2, 3]})
        result = complete_months(monthly, pd.Timestamp("2011-12-09"))
        self.assertEqual(result["revenue"].tolist(), [1, 2])

    def test_keeps_final_month_if_observation_reaches_month_end(self):
        monthly = pd.DataFrame({"order_month": pd.to_datetime(["2011-11-01", "2011-12-01"]), "revenue": [1, 2]})
        self.assertEqual(len(complete_months(monthly, pd.Timestamp("2011-12-31"))), 2)

    def test_original_experiment_is_not_feasible(self):
        baseline = 0.2374323279195669
        original = sample_size_two_proportions(baseline, baseline * 1.2)
        self.assertGreater(original * 2, 1293)
        effect = feasible_mde(baseline, 1293)
        self.assertGreater(effect, baseline * .2)
        self.assertLessEqual(sample_size_two_proportions(baseline, baseline + effect), 1293 // 2)

    def test_feasible_mde_rejects_tiny_pool(self):
        with self.assertRaises(ValueError):
            feasible_mde(.2, 3)

    def test_committed_scenario_uses_last_three_complete_months(self):
        monthly = pd.read_csv(self.data_dir / "monthly_kpis.csv", parse_dates=["order_month"])
        overview = pd.read_csv(self.data_dir / "overview_metrics.csv")
        scenarios = pd.read_csv(self.data_dir / "growth_scenarios.csv")
        complete = complete_months(monthly, pd.Timestamp(overview.loc[0, "date_end"]))
        aov_scenario = scenarios.loc[scenarios["scenario"].str.contains("AOV")].iloc[0]
        self.assertAlmostEqual(aov_scenario["baseline"], complete.tail(3)["revenue"].sum(), places=2)

    def test_committed_experiment_discloses_infeasibility(self):
        ab = pd.read_csv(self.data_dir / "ab_test_design.csv").iloc[0]
        self.assertFalse(bool(ab["sample_feasible"]))
        self.assertGreater(ab["required_total_sample"], ab["eligible_customers"])
        self.assertEqual(int(ab["available_per_variant"]), int(ab["eligible_customers"]) // 2)


if __name__ == "__main__":
    unittest.main()
