import unittest
import re
from app import app

class TestRibbonSystem(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_header_actions_no_export_buttons(self):
        """Header actions must NOT contain the 4 export buttons."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Find header-actions block
        m = re.search(r'<div class="header-actions">(.*?)<div class="user-box">', content, re.DOTALL)
        self.assertIsNotNone(m, "header-actions block must exist")
        header_actions_html = m.group(1)

        self.assertNotIn("exportSyllabusPdf()", header_actions_html, "Export Syllabus button must be removed from header")
        self.assertNotIn("exportCloReportPdf()", header_actions_html, "Export CLO Report PDF must be removed from header")
        self.assertNotIn("exportCloReportExcel()", header_actions_html, "Export CLO Report Excel must be removed from header")
        self.assertNotIn("exportExcelWorkbook()", header_actions_html, "Export Class Record Excel must be removed from header")

    def test_ribbon_system_structure(self):
        """Ribbon system must have Dashboard, Syllabus Creator & Steps, and Requests for Approval."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Ribbon system container
        self.assertIn('id="ribbonSystem"', content)
        self.assertIn('class="ribbon-system"', content)

        # Level 1: Ribbon tabs
        self.assertIn('id="ribbonTabDashboard"', content)
        self.assertIn('id="ribbonTabSyllabus"', content)
        self.assertIn('id="tabBtnApprovals"', content)
        self.assertIn('id="approvalsBadge"', content)

        # Level 2: Ribbon command bands
        self.assertIn('id="ribbonBandDashboard"', content)
        self.assertIn('id="ribbonBandSyllabus"', content)
        self.assertIn('id="ribbonBandApprovals"', content)

        # 7 Corresponding Steps in Syllabus Creator Ribbon
        self.assertIn('id="stepBtnTabSyllabus"', content)
        self.assertIn('id="stepBtnTabAssessments"', content)
        self.assertIn('id="stepBtnTabGradebook"', content)
        self.assertIn('id="stepBtnTabReceiptAck"', content)
        self.assertIn('id="stepBtnTabTos"', content)
        self.assertIn('id="stepBtnTabCloreport"', content)
        self.assertIn('id="stepBtnTabCqi"', content)

        # Official Output Exports in Syllabus Creator Ribbon
        self.assertIn('id="ribbonBtnExportSyllabus"', content)
        self.assertIn('id="ribbonBtnExportClassRecord"', content)
        self.assertIn('id="ribbonBtnExportCloPdf"', content)
        self.assertIn('id="ribbonBtnExportCloExcel"', content)

        # Dynamic step actions container
        self.assertIn('id="ribbonContextTitle"', content)
        self.assertIn('id="ribbonStepActions"', content)

    def test_stepper_order_and_sequential_numbering(self):
        """Test stepper ordering and sequential 1 to 7 badge numbering."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        m = re.search(r'<div class="ribbon-group-content ribbon-steps">(.*?)</div>\s*</div>', content, re.DOTALL)
        self.assertIsNotNone(m, "ribbon-steps container must exist")
        steps_html = m.group(1)

        # Check order of button IDs
        expected_ids = [
            "stepBtnTabSyllabus",
            "stepBtnTabAssessments",
            "stepBtnTabGradebook",
            "stepBtnTabReceiptAck",
            "stepBtnTabTos",
            "stepBtnTabCloreport",
            "stepBtnTabCqi"
        ]

        pos = -1
        for btn_id in expected_ids:
            btn_pos = steps_html.find(f'id="{btn_id}"')
            self.assertNotEqual(btn_pos, -1, f"Button {btn_id} not found in ribbon-steps")
            self.assertGreater(btn_pos, pos, f"Button {btn_id} must appear after previous step")
            pos = btn_pos

        # Check sequential badge numbers
        matches = re.findall(r'<button[^>]+id="([^"]+)"[^>]*>.*?<span class="step-num">([^<]+)</span>', steps_html, re.DOTALL)
        expected_badges = [
            ("stepBtnTabSyllabus", "1"),
            ("stepBtnTabAssessments", "2"),
            ("stepBtnTabGradebook", "3"),
            ("stepBtnTabReceiptAck", "4"),
            ("stepBtnTabTos", "5"),
            ("stepBtnTabCloreport", "6"),
            ("stepBtnTabCqi", "7")
        ]
        self.assertEqual(len(matches), 7)
        for i, (btn_id, num) in enumerate(expected_badges):
            self.assertEqual(matches[i][0], btn_id)
            self.assertEqual(matches[i][1].strip(), num)

        # Verify TOS routes to tab-tos
        self.assertIn('onclick="switchSyllabusStep(\'tab-tos\')"', steps_html)

    def test_exports_in_relevant_parts(self):
        """Export buttons must be present in the relevant sections/cards."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Step 1 (tab-syllabus) has export syllabus buttons
        tab_syl_idx = content.find('id="tab-syllabus"')
        tab_assess_idx = content.find('id="tab-assessments"')
        tab_syl_block = content[tab_syl_idx:tab_assess_idx]
        self.assertIn("exportSyllabusPdf()", tab_syl_block, "Step 1 must have Export Syllabus PDF button")

        # Step 3 (tab-gradebook) has export class record button
        tab_gb_idx = content.find('id="tab-gradebook"')
        tab_receipt_idx = content.find('id="tab-receipt-ack"')
        tab_gb_block = content[tab_gb_idx:tab_receipt_idx]
        self.assertIn("exportExcelWorkbook()", tab_gb_block, "Step 3 must have Export Class Record button")

        # Step 6 (tab-cloreport) has CLO export buttons
        tab_cqi_idx = content.find('id="tab-cqi"')
        tab_clo_idx = content.find('id="tab-cloreport"')
        tab_clo_block = content[tab_clo_idx:tab_cqi_idx]
        self.assertIn("exportCloReportPdf()", tab_clo_block, "Step 6 must have Export CLO Report PDF")
        self.assertIn("exportCloReportExcel()", tab_clo_block, "Step 6 must have Export CLO Report Excel")

    def test_javascript_ribbon_functions(self):
        """JavaScript ribbon switching functions must be present."""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("function switchRibbon(ribbonId, targetTabId)", content)
        self.assertIn("function switchSyllabusStep(stepTabId)", content)
        self.assertIn("function updateSyllabusStepUI(stepTabId)", content)
        self.assertIn("function switchTabPanel(tabId)", content)
        self.assertIn("function switchTab(tabId, btnEl)", content)

    def test_rendered_index_page(self):
        """Logged-in faculty gets 200 and page renders ribbon bar."""
        with self.client.session_transaction() as sess:
            sess["username"] = "faculty_tano"
            sess["role"] = "faculty"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn('id="ribbonSystem"', html)
        self.assertIn('id="ribbonTabDashboard"', html)
        self.assertIn('id="ribbonTabSyllabus"', html)
        self.assertIn('id="tabBtnApprovals"', html)
        self.assertIn('id="stepBtnTabSyllabus"', html)
        self.assertIn('id="stepBtnTabGradebook"', html)
        self.assertIn('id="stepBtnTabTos"', html)

if __name__ == "__main__":
    unittest.main()
