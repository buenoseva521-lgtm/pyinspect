import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pyinspect import Project, RelationType
from pyinspect.exporters import to_dot, to_json


FIXTURE = Path(__file__).parent / "fixtures" / "sample_project"


class ProjectTests(unittest.TestCase):
    def test_scan_extracts_entities_and_calls(self):
        project = Project(FIXTURE)
        result = project.scan()
        self.assertEqual(len(result.files), 2)
        self.assertTrue(project.find_function("process"))
        self.assertTrue(any(e.type == RelationType.CALLS for e in result.edges))
        self.assertIn("unused_function", {i.kind for i in result.issues})

    def test_json_and_dot_exports(self):
        result = Project(FIXTURE).scan()
        payload = json.loads(to_json(result))
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertIn("digraph PyInspect", to_dot(result))

    def test_cache_is_written(self):
        Project(FIXTURE).scan()
        self.assertTrue((FIXTURE / ".pyinspect-cache.json").exists())

    def test_circular_import(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("import b\n")
            (root / "b.py").write_text("import a\n")
            result = Project(root).scan()
            self.assertTrue(any(i.kind == "circular_import" for i in result.issues))


if __name__ == "__main__":
    unittest.main()
