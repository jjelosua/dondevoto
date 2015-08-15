import sys
from difflib import *
import heapq
from datetime import datetime
import Queue
import threading
import dataset


def get_close_matches_with_score(word, possibilities, n=3, cutoff=0.6):
    """ Lo mismo que difflib.get_close_matches
        pero tambien retorna el score """
    if not n > 0:
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


db = dataset.connect()
establecimientos = db['establecimientos']
escuelas = db['escuelasutf8']
weighted_matches = db['weighted_matches']
dedupe_matches = db['dedupe_matches']
persist_queue = Queue.Queue()


@memoize
def escuelas_in_distrito(id_distrito, id_seccion):
    # Use the calculated district and section
    # over escuelasutf8 and filter out results
    q = """ select * from escuelasutf8 esc
            where esc.id_distrito = '%s'
              and esc.id_seccion = '%s'
              and esc.ogc_fid not in (select escuela_id from dedupe_matches)
        """ % (id_distrito, id_seccion)
    results = list(db.query(q))

    return results


def log(msg):
    print >>sys.stderr, msg


def canon(s):
    return s.lower().replace(' ', '')


def match_persister():
    while True:
        try:
            establecimiento, matches = persist_queue.get(block=True, timeout=3)
            for m in matches:
                weighted_matches.insert({
                    'establecimiento_id': establecimiento['id'],
                    'escuela_id': m[1]['ogc_fid'],
                    'score': m[0],
                    'match_source': 0
                })
            persist_queue.task_done()
        except Queue.Empty:
            log("Empty queue after 3 seconds, should be enough")
            break


# def canon_func(est):
#     '''return canonized version of polling stations
#        for the get_close_matches function'''
#     d = {str(k): v for k, v in est.iteritems()}
#     canonized = canon("%(nombre)s%(direccion)s" % d)
#     return canonized


def do_match():
    total_establecimientos = len(establecimientos)
    log('TOTAL: %s' % total_establecimientos)
    current_item = 0
    current_time = datetime.now()

    for e in establecimientos:
        match_in = []
        canon_func = None
        matches = []
        coeff = 1

        if current_item % 100 == 0:
            log('processing item %i/%i (+%s seconds)'
                % (current_item, total_establecimientos,
                   (datetime.now() - current_time).seconds))
            current_time = datetime.now()

        current_item += 1

        canon_func = lambda est: canon("%(nombre)s%(direccion)s") % {str(k): v for k, v in est.iteritems()}
        test = escuelas_in_distrito(e['id_distrito'], e['id_seccion'])
        match_in = {canon_func(i): i
                    for i in escuelas_in_distrito(
                        e['id_distrito'],
                        e['id_seccion'])}

        _matches = get_close_matches_with_score(
            canon_func({'nombre': e[u'nombre'],
                       'direccion': e[u'direccion']}),
            match_in.keys(),
            5,
            0.5)

        matches += [(score * coeff, match_in[result])
                    for score, result in _matches]

        # log('Matching "%s - %s (%s)"'
        #     % (e['establecimiento'], e['direccion'], e['localidad']))
        # for m in matches:
        #     log('\t%.2f %s - %s (%s)'
        #         % (m[0], m[1]['nombre'],
        #            m[1]['ndomiciio'],
        #            m[1]['localidad']))

        persist_queue.put((e, matches))


if __name__ == '__main__':
    t_main = threading.Thread(target=do_match)
    t_persister = threading.Thread(target=match_persister)
    t_main.daemon = True
    t_persister.daemon = True
    t_main.start()
    t_persister.start()

    for t in [t_main, t_persister]:
        t.join()
