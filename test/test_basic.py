import unittest


def df(*v):
    """Return a path to a test data file"""
    from os.path import dirname, join

    return join(dirname(__file__), 'test_data',*v)

class BasicTest(unittest.TestCase):

    def test_row_intuition(self):

        from csv import DictReader
        from rowgenerators import RowGenerator
        from tableintuit import TypeIntuiter, RowIntuiter

        with open(df('rows','sources.csv')) as f:

            for e in DictReader(f):
                rows = list(RowGenerator(df('rows',e['path'])))
                self.assertEquals( int(e['rows']), len(rows))

                ri = RowIntuiter()
                ri.run(rows)
                self.assertEqual(int(e['start']),  ri.start_line)
                self.assertEqual(e['comments'],  ','.join( str(e) for e in ri.comment_lines))
                self.assertEqual(e['headers'], ','.join(str(e) for e in ri.header_lines))

    def test_row_intuition_rowgen(self):
        """Like test_row_intuition, but the dict read rows from the csv file
        are direct input to a RowGenerator"""
        from csv import DictReader
        from rowgenerators import RowGenerator
        from tableintuit import TypeIntuiter, RowIntuiter, RowIntuitError

        with open(df('rowgen_sources.csv')) as f:
            for e in DictReader(f):
                #print e['name']
                gen = RowGenerator(**e)

                rows = list(gen)

                self.assertEquals(int(e['n_rows']), len(rows))

                try:
                    ri = RowIntuiter()
                    ri.run(rows)
                except RowIntuitError as exc:
                    print "Error: ", e, exc

                if e['expect_start']:
                    self.assertEqual(int(e['expect_start']), ri.start_line)

                if e['expect_headers']:
                    self.assertEquals(e['expect_headers'], ','.join(str(e) for e in ri.header_lines))


    def test_intuition_fails(self):
        from rowgenerators import RowGenerator
        from tableintuit import  RowIntuiter

        url = 'http://public.source.civicknowledge.com/example.com/row_intuit/headers_1.csv'
        ri = RowIntuiter().run(list(RowGenerator(url)))

        print ri.start_line, ri.header_lines

    def test_urltype(self):

        from rowgenerators import RowGenerator as rg

        self.assertEqual('file', rg('/foo/bar.zip').urltype)
        self.assertEqual('file', rg('file:///foo/bar.zip').urltype)
        self.assertEqual('gs', rg('gs://foo/bar.zip').urltype)
        self.assertEqual('socrata', rg('socrata://foo/bar.zip').urltype)
        self.assertEqual('http', rg('http://foo/bar.zip').urltype)
        self.assertEqual('http', rg('https://foo/bar.zip').urltype)

    def test_urlfiletype(self):
        from rowgenerators import RowGenerator as rg

        self.assertEqual('csv', rg('/foo/bar.csv').filetype)
        self.assertEqual('zip', rg('file:///foo/bar.zip#foobar.csv').filetype)
        self.assertEqual('xls', rg('gs://foo/bar.xls?foo=bar').filetype)

    def test_filetype(self):

        from rowgenerators import RowGenerator as rg

        self.assertEqual('csv', rg('/foo/bar.csv').filetype)
        self.assertEqual('csv', rg('file:///foo/bar.zip#foobar.csv').filetype)
        self.assertEqual('xls', rg('gs://foo/bar.xls?foo=bar').filetype)

    def test_selective(self):
        from csv import DictReader
        from rowgenerators import RowGenerator
        from tableintuit import RowIntuiter
        from tableintuit import SelectiveRowGenerator
        from itertools import islice

        rows = [ ['header1']] + [ ['header2']]+ [ [i] for i in range(10) ]

        rg = SelectiveRowGenerator(rows, start=5, headers=[0,1], comments=[2,3], end=9)

        self.assertEquals([[u'header1 header2'], [3], [4], [5], [6], [7], [8], [9]], list(rg))
        self.assertEqual([['header1'], ['header2']], rg.headers)
        self.assertEqual([[0],[1]], rg.comments)

        with open(df('rowgen_sources.csv')) as f:
            sources = { e['name']:e for e in DictReader(f)}

        rg = RowGenerator(**sources['rentcsv'])
        ri = RowIntuiter().run(list(rg))

        rows = list(islice(SelectiveRowGenerator(rg, **ri.spec), 100))

        # First row is the header
        self.assertEqual([u'id', u'gvid', u'renter cost_gt_30', u'renter cost_gt_30_cv', u'owner cost_gt_30_pct',
                          u'owner cost_gt_30_pct_cv'],
                         rows[0])

        # Second is the first data row, which is actually the 6th row in the file
        self.assertEqual([u'1', u'0O0P01', u'1447', u'13.6176070905', u'42.2481751825', u'8.272140707'],
                         rows[1])

    def test_type_intuition(self):
        from csv import DictReader
        from rowgenerators import RowGenerator
        from tableintuit import SelectiveRowGenerator, TypeIntuiter
        from six import binary_type, text_type

        with open(df('stat_sources.csv')) as f:
            def proc_dict(d):
                if d['headers']:
                    d['headers'] = [int(e) for e in d['headers'].split(',')]
                if d['start']:
                    d['start'] = int(d['start'])
                return d

            sources = {e['name']: proc_dict(e) for e in DictReader(f)}

        def run_ti(e):
            rg = RowGenerator(**e)
            srg = SelectiveRowGenerator(rg, **e)
            rows = list(srg)
            ti = TypeIntuiter().run(rows)

            return ti

        ti = run_ti(sources['types1'])
        self.assertEquals(13,ti['float'].type_counts[float])
        self.assertEquals(0, ti['float'].type_counts[int])
        self.assertEquals(0, ti['float'].type_counts[str])
        self.assertEquals(0,ti['int'].type_counts[float])
        self.assertEquals(13, ti['int'].type_counts[int])
        self.assertEquals(0, ti['int'].type_counts[unicode])

        ti = run_ti(sources['namesu8'])
        self.assertEquals(binary_type, ti[0].resolved_type)
        self.assertEquals(binary_type, ti[1].resolved_type)
        self.assertEquals(52, ti[2].count)
        self.assertEquals(20, ti[2].type_counts[str])
        self.assertEquals(32, ti[2].type_counts[unicode])
        self.assertEquals(text_type, ti[2].resolved_type)
        self.assertEquals(2, ti[3].type_counts[str])
        self.assertEquals(50, ti[3].type_counts[unicode])
        self.assertEquals(text_type, ti[3].resolved_type)


    def test_stats(self):
        from csv import DictReader
        from rowgenerators import RowGenerator
        from tableintuit import SelectiveRowGenerator, TypeIntuiter, Stats

        with open(df('stat_sources.csv')) as f:
            def proc_dict(d):
                if d['headers']:
                    d['headers'] = [ int(e) for e in d['headers'].split(',')]
                if d['start']:
                    d['start'] = int(d['start'])
                return d

            sources = { e['name']:proc_dict(e) for e in DictReader(f)}

        for k, e in sources.items():

            rg = RowGenerator(**e)
            srg = SelectiveRowGenerator(rg, **e)
            rows = list(srg)
            print '----'
            print e['name']
            print len(rows)
            print rows[0]
            print rows[1]

            ti = TypeIntuiter().run(rows)

            header = [ c.header for c in ti.columns]

            schema = [(c.header, c.resolved_type) for c in ti.columns]

            stats = Stats(schema).run(dict(zip(header, row)) for row in rows)

            print unicode(stats).encode('utf8')

if __name__ == '__main__':
    unittest.main()