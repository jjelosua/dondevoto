import sys
from difflib import *
import heapq
from datetime import datetime
import Queue
import threading
import csv

import dataset

def get_close_matches_with_score(word, possibilities, n=3, cutoff=0.6):
    """ Lo mismo que difflib.get_close_matches
        pero tambien retorna el score """
    if not n >  0:
        raise ValueError("n must be > 0: %r" % (n,))
    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))
    result = []
    s = SequenceMatcher()
    s.set_seq2(word)
    for x in possibilities:
        s.set_seq1(x)
        if s.real_quick_ratio() >= cutoff and \
           s.quick_ratio() >= cutoff and \
           s.ratio() >= cutoff:
            result.append((s.ratio(), x))

    # Move the best scorers to head of list
    result = heapq.nlargest(n, result)
    return result


def memoize(f):
    """ Memoization decorator for functions taking one or more arguments. """
    class memodict(dict):
        def __init__(self, f):
            self.f = f
        def __call__(self, *args):
            return self[args]
        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret
    return memodict(f)

db = dataset.connect('postgresql://jjelosua@localhost:5432/elecciones2015')
dine_estab = db['establecimientos']
escuelas = db['escuelasutf8']
weighted_matches = db['weighted_matches']
dedupe_matches = db['dedupe_matches']


@memoize
def escuelas_in_distrito(dne_seccion_id, dne_distrito_id):
    # q = """ select * from escuelasutf8 where
    #         st_within(wkb_geometry_4326, (select st_collect(o.wkb_geometry) as geom
    #         from divisiones_administrativas o
    #         where o.dne_seccion_id = %s
    #           and o.dne_distrito_id = %s
    #         group by o.wkb_geometry))
    #     """ % (dne_seccion_id, dne_distrito_id)
    # Use the calculated district and section over escuelasutf8 and filter out results
    q = """ select * from escuelasutf8 esc
            where esc.dne_seccion_id = %s
              and esc.dne_distrito_id = %s
              and esc.ogc_fid not in (select escuela_id from dedupe_matches)
        """ % (dne_seccion_id, dne_distrito_id)
    results = list(db.query(q))

    return results


def log(msg):
    print >>sys.stderr, msg

def canon(s):
    return s.lower().replace(' ', '')

persist_queue = Queue.Queue()
def match_persister():
    while True:
        establecimiento, matches = persist_queue.get()
        for m in matches:
            weighted_matches.insert({
                'establecimiento_id': establecimiento['id'],
                'escuela_id': m[1]['ogc_fid'],
                'score': m[0],
                'match_source': 0
            })
        persist_queue.task_done()

def do_match():
    total_establecimientos = len(dine_estab)
    log('TOTAL: %s' % total_establecimientos)
    match_count = 0
    current_item = 0
    current_time = datetime.now()

    for e in dine_estab:
        match_in = []
        canon_func = None

        matches = []
        coeff = 1

        if current_item % 1000 == 0:
            log('processing item %i/%i (+%s seconds)' % (current_item, total_establecimientos, (datetime.now() - current_time).seconds))
            current_time = datetime.now()

        current_item += 1


        canon_func = lambda est: canon("%(nombre)s%(ndomiciio)s") % { str(k):v for k,v in est.iteritems() }
        match_in = { canon_func(i): i
                     for i in escuelas_in_distrito(e['dne_seccion_id'],
                                                   e['dne_distrito_id']) }
        

        _matches = get_close_matches_with_score(canon_func({'nombre': e[u'establecimiento'],
                                                            'ndomiciio': e[u'direccion']}),
                                                match_in.keys(),
                                                5,
                                                0.5)

        matches += [(score * coeff, match_in[result]) for score, result in _matches]

        #log('Matching "%s - %s (%s)"' % (e['establecimiento'], e['direccion'], e['localidad']))
        #for m in matches:
        #    log('\t%.2f %s - %s (%s)' % (m[0], m[1]['nombre'], m[1]['ndomiciio'], m[1]['localidad']))

        persist_queue.put((e, matches))


if __name__ == '__main__':
    t_main = threading.Thread(target=do_match)
    t_persister = threading.Thread(target=match_persister)
    t_main.daemon = True; t_persister.daemon = True
    t_main.start(); t_persister.start()

    for t in [t_main,t_persister]: t.join()
