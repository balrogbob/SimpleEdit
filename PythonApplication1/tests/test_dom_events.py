import unittest

from PythonApplication1.jsmini import make_context
from PythonApplication1.tests.test_base import CleanTestCase

class TestDOMEvents(CleanTestCase):
    def test_document_add_remove_attach_dispatch(self):
        ctx = make_context()
        self.ctx = ctx
        doc = ctx['document']
        
        print(f"[TEST] doc type: {type(doc)}")
        print(f"[TEST] doc['dispatchEvent'] is: {doc['dispatchEvent']}")
        print(f"[TEST] doc['dispatchEvent'] id: {id(doc['dispatchEvent'])}")
        
        called = {'count': 0}
        def handler(ev):
            called['count'] += 1
    
        # add listener and dispatch
        doc['addEventListener']('myevent', handler)
        doc['dispatchEvent']('myevent')
        self.assertEqual(called['count'], 1)
if __name__ == '__main__':
    unittest.main()