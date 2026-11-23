"""Guard the static HTML structure and its explicit accessible field labels."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
END_TAG = re.compile(r'</\s*([a-zA-Z][\w:-]*)([^>]*)>')


def invalid_closing_tags(source):
    # HTMLParser repairs/ignores closing-tag attributes instead of rejecting them.
    return [match.group(0) for match in END_TAG.finditer(source) if match.group(2).strip()]


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack=[]
        self.errors=[]
        self.ids={}
        self.labels={}
        self.selects={}
        self.current_label=None
        self.coordinate_ancestors={}

    def handle_starttag(self,tag,attributes):
        attrs=dict(attributes)
        if ident:=attrs.get('id'):
            if ident in self.ids: self.errors.append('Duplicate id: '+ident)
            self.ids[ident]=(tag,attrs)
            if ident in ('latitude','longitude','radius'):
                self.coordinate_ancestors[ident]=self.stack.copy()
        if tag=='label':
            self.current_label=attrs.get('for')
            if self.current_label: self.labels[self.current_label]=''
        if tag=='select': self.selects[attrs.get('id')]=[]
        if tag=='option':
            parent=next((ident for name,ident in reversed(self.stack) if name=='select'),None)
            if not parent: self.errors.append('Option outside a select')
            else: self.selects[parent].append(attrs.get('value'))
        if tag not in VOID: self.stack.append((tag,attrs.get('id')))

    def handle_startendtag(self,tag,attrs):
        # SVG paths/circles in this document intentionally self-close.
        pass

    def handle_endtag(self,tag):
        if tag=='label': self.current_label=None
        if tag in VOID: self.errors.append('Void element closed: '+tag)
        elif not self.stack or self.stack[-1][0]!=tag:
            self.errors.append('Unexpected closing tag: '+tag)
        else: self.stack.pop()

    def handle_data(self,data):
        if self.current_label: self.labels[self.current_label]+=data


class HTMLTests(unittest.TestCase):
    def setUp(self):
        self.source=(ROOT/'web/index.html').read_text()
        self.doc=Structure()
        self.doc.feed(self.source)

    def test_closing_tag_attributes_are_rejected(self):
        self.assertEqual(invalid_closing_tags(self.source),[])
        self.assertEqual(invalid_closing_tags('<option>Any</option value="yes">Yes</option>'),['</option value="yes">'])

    def test_markup_is_balanced_and_ids_are_unique(self):
        self.assertEqual(self.doc.errors,[])
        self.assertEqual(self.doc.stack,[])

    def test_fields_have_explicit_labels_and_all_wheelchair_states(self):
        expected={'region':'Region','capture':'Dated capture','query':'Find a name, operator or tag',
                  'wheelchair':'Wheelchair','access':'Access','fee':'Fee','changing':'Changing table',
                  'latitude':'Latitude','longitude':'Longitude','radius':'Within'}
        for ident,text in expected.items():
            with self.subTest(field=ident):
                self.assertEqual(self.doc.labels[ident].strip(),text)
                self.assertIn(self.doc.ids[ident][0],('input','select'))
        self.assertEqual(self.doc.selects['wheelchair'],['','yes','limited','no','unknown'])

    def test_coordinate_inputs_are_inside_the_disclosure_form(self):
        for ident,parents in self.doc.coordinate_ancestors.items():
            with self.subTest(field=ident):
                self.assertIn(('form','point-form'),parents)
                self.assertTrue(any(tag=='details' for tag,_ in parents))
                self.assertFalse(any(tag=='summary' for tag,_ in parents))
        self.assertEqual(set(self.doc.coordinate_ancestors),{'latitude','longitude','radius'})


if __name__=='__main__': unittest.main()
