import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("render_weekly", ROOT / "scripts/render_weekly.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RenderRules(unittest.TestCase):
    def test_raw_html_is_not_executed(self):
        result = module.inline('<script>alert(1)</script>', Path('.'))
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_unsafe_link_scheme_rejected(self):
        with self.assertRaises(ValueError):
            module.inline('[bad](javascript:alert)', Path('.'))

    def test_table_separator_is_not_rendered_as_content(self):
        items = list(module.blocks('| A | B |\n|---|---|\n| 1 | 2 |'))
        self.assertEqual(items, [('table', [['A', 'B'], ['1', '2']])])

    def test_invalid_font_is_an_explicit_error(self):
        with self.assertRaises(ValueError):
            module.find_font(Path('no-such-font.ttf'))

    def test_document_glyphs_are_checked_beyond_title(self):
        title_only = {ord(ch): 1 for ch in '产品周刊'}
        with self.assertRaises(ValueError):
            module.require_glyphs('产品周刊 技术前沿', title_only)
        module.require_glyphs('产品周刊\n', title_only)

    def test_headings_and_paragraphs_remain_in_order(self):
        items = list(module.blocks('# 标题\n\n正文\n\n## 下一节\n\n继续'))
        self.assertEqual([kind for kind, _ in items], ['heading', 'paragraph', 'heading', 'paragraph'])


if __name__ == '__main__':
    unittest.main()
