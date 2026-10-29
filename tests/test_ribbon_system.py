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

        # 5 Corresponding Steps in Syllabus Creator Ribbon
        self.assertIn('id="stepBtnTabSyllabus"', content)
        self.assertIn('id="stepBtnTabAssessments"', content)
        self.assertIn('id="stepBtnTabGradebook"', content)
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
        tab_clo_idx = content.find('id="tab-cloreport"')
        tab_gb_block = content[tab_gb_idx:tab_clo_idx]
        self.assertIn("exportExcelWorkbook()", tab_gb_block, "Step 3 must have Export Class Record button")

        # Step 4 (tab-cloreport) has CLO export buttons
        tab_cqi_idx = content.find('id="tab-cqi"')
        tab_clo_block = content[tab_clo_idx:tab_cqi_idx]
        self.assertIn("exportCloReportPdf()", tab_clo_block, "Step 4 must have Export CLO Report PDF")
        self.assertIn("exportCloReportExcel()", tab_clo_block, "Step 4 must have Export CLO Report Excel")

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

if __name__ == "__main__":
    unittest.main()
