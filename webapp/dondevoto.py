# coding: utf-8
from collections import OrderedDict
import os
import re
import dataset
import flask
from flask import Flask, render_template, abort, request
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.formparser import parse_form_data
from werkzeug.wsgi import get_input_stream
from io import BytesIO
from wsgiauth import basic
import json

# Umbral para considerar válidas a los matches calculados por el algoritmo
MATCH_THRESHOLD = 0.95
# Umbral para detectar inconsistencias en la geolocalizacion
DISTANCE_THRESHOLD = 100
DELETE_MATCHES_QUERY = """ DELETE
                           FROM weighted_matches
                           WHERE establecimiento_id = %d
                           AND match_source = 1 """


class MethodMiddleware(object):
    """Don't actually do this. The disadvantages are not worth it."""
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'].upper() == 'POST':
            environ['wsgi.input'] = stream = \
                BytesIO(get_input_stream(environ).read())
            formdata = parse_form_data(environ)[1]
            stream.seek(0)

            method = formdata.get('_method', '').upper()
            if method in ('GET', 'POST', 'PUT', 'DELETE'):
                environ['REQUEST_METHOD'] = method

        return self.app(environ, start_response)


def authfunc(env, username, password):
    # TODO guardar username en env, para guardar el autor de los matches
    return password == os.environ.get('DONDEVOTO_PASSWORD', 'dondevoto')

app = Flask(__name__)
# Add debug mode
app.debug = True
app.wsgi_app = basic.basic(
    'dondevoto',
    authfunc)(MethodMiddleware(app.wsgi_app))
app.wsgi_app = ProxyFix(app.wsgi_app)

# DEFINE ENVVAR DATABASE_URL
db = dataset.connect()


def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file), arcname=file)


def provincias_distritos():
    """ mapa distrito -> [seccion, ..., seccion] """

    rv = OrderedDict()
    q = """
        SELECT da.id_distrito,
               da.desc_distrito,
               da.id_seccion,
               da.desc_seccion,
               count(e.id) AS estab_count,
               count(wm.id) AS matches_count
        FROM divisiones_administrativas da
        INNER JOIN establecimientos e
        USING (id_distrito, id_seccion)
        LEFT OUTER JOIN weighted_matches wm
            ON wm.establecimiento_id = e.id
            AND wm.score = 1 and wm.match_source = 1
        GROUP BY da.id_distrito,
                 da.desc_distrito,
                 da.id_seccion,
                 da.desc_seccion
        ORDER BY id_distrito,
                 id_seccion
        """

    for d in db.query(q):
        k = (d['id_distrito'], d['desc_distrito'],)
        if k not in rv:
            rv[k] = []
        rv[k].append((
            d['id_distrito'],
            d['id_seccion'],
            d['desc_seccion'],
            d['estab_count'],
            d['matches_count']))
    return rv


@app.route("/")
@app.route("/<id_distrito>/<id_seccion>")
def index(id_distrito=None, id_seccion=None):
    return render_template('index.html',
                           provincias_distritos=provincias_distritos(),
                           dne_distrito_id=id_distrito,
                           dne_seccion_id=id_seccion)


@app.route("/completion")
def completion():
    q = """
        SELECT da.id_distrito,
               da.desc_distrito,
               count(e.*) AS estab_count,
               count(wm.*) AS matches_count
        FROM divisiones_administrativas da
        INNER JOIN establecimientos e
            USING(id_distrito, id_seccion)
        LEFT OUTER JOIN weighted_matches wm
            ON wm.establecimiento_id = e.id
            AND wm.score = 1 AND wm.match_source = 1
        GROUP BY da.id_distrito, da.desc_distrito
        ORDER BY da.id_distrito
    """

    return flask.Response(flask.json.dumps(list(db.query(q))),
                          mimetype='application/json')


@app.route("/seccion/<distrito_id>/<seccion_id>")
def seccion_info(distrito_id, seccion_id):
    q = """
        SELECT *,
        st_asgeojson(st_setsrid(ST_Translate(
            ST_Scale(wkb_geometry_4326, 1.1, 1.1),
            ST_X(ST_Centroid(wkb_geometry_4326))*(1-1.1),
            ST_Y(ST_Centroid(wkb_geometry_4326))*(1-1.1)), 900913)) AS geojson,
        st_asgeojson(st_envelope(ST_Translate(
            ST_Scale(wkb_geometry_4326, 1.1, 1.1),
            ST_X(ST_Centroid(wkb_geometry_4326))*(1 - 1.1),
            ST_Y(ST_Centroid(wkb_geometry_4326))*(1 - 1.1)))) AS bounds
        FROM divisiones_administrativas
        WHERE id_distrito = '%s'
        AND id_seccion = '%s'
    """ % (distrito_id, seccion_id)

    r = [dict(e.items() + [('geojson', json.loads(e['geojson'])),
                           ('wkb_geometry_4326', ''),
                           ('bounds', json.loads(e['bounds']))])
         for e in db.query(q)][0]

    return flask.Response(flask.json.dumps(r),
                          mimetype='application/json')


@app.route("/establecimientos/<distrito_id>/<seccion_id>")
def establecimientos_by_distrito_and_seccion(distrito_id, seccion_id):
    q = """
        SELECT e.id, e.nombre, e.direccion, e.localidad,
        e.id_circuito, e.latitud, e.longitud,
        count(CASE WHEN wm.score >= 1 then 1 end) AS match_count,
        count(CASE WHEN wm.score < 1
              AND wm.score >= 0.95 Then 1 end) AS guess_count,
        count(CASE WHEN st_distance(esc.wkb_geometry_4326::geography,
                                    e.wkb_geometry_4326::geography) <= %d
                   Then 1 end) AS closeby_count
        FROM establecimientos e
        LEFT OUTER JOIN weighted_matches wm
          ON (wm.establecimiento_id = e.id AND wm.score >= %f)
        LEFT OUTER JOIN escuelasutf8 esc
          ON (wm.escuela_id = esc.ogc_fid)
        WHERE e.id_distrito = '%s'
        AND e.id_seccion = '%s'
        GROUP BY e.id, e.nombre, e.direccion, e.localidad, e.id_circuito,
                 e.latitud, e.longitud
        ORDER BY e.id_circuito """ % (DISTANCE_THRESHOLD, MATCH_THRESHOLD,
                                      distrito_id, seccion_id)

    return flask.Response(flask.json.dumps(list(db.query(q))),
                          mimetype='application/json')


@app.route("/matches/<int:establecimiento_id>", methods=['GET'])
def matched_escuelas(establecimiento_id):
    """ obtener los matches para un establecimiento """

    q = """
       SELECT
            wm.score,
            wm.establecimiento_id,
            esc.*,
            st_asgeojson(esc.wkb_geometry_4326) AS geojson,
            (CASE WHEN wm.match_source >= 1 THEN 1
             WHEN wm.score > %f AND wm.match_source = 0 THEN 1
             ELSE 0
            END) AS is_match
       FROM weighted_matches wm
       INNER JOIN establecimientos e
            ON e.id = wm.establecimiento_id
       INNER JOIN escuelasutf8 esc
            ON esc.ogc_fid = wm.escuela_id
       WHERE wm.establecimiento_id = %d
       ORDER BY wm.score DESC
       """ % (MATCH_THRESHOLD, establecimiento_id)

    r = [dict(e.items() + [('geojson', json.loads(e['geojson']))])
         for e in db.query(q)]

    return flask.Response(flask.json.dumps(r),
                          mimetype='application/json')


@app.route("/places/<distrito_id>/<seccion_id>")
def places_for_distrito_and_seccion(distrito_id, seccion_id):
    """ Todos los places (escuelas) para este distrito y seccion """
    # Add school number search on top
    extract_integer = re.compile(r"^.*?(\d+)").match
    match = extract_integer(request.args.get('nombre'))
    if match:
        n = int(match.group(1))
    else:
        n = -1

    search_type = request.args.get('search_type')
    nombre = request.args.get('nombre').replace("'", "''")
    direccion = request.args.get('direccion').replace("'", "''")
    localidad = request.args.get('localidad').replace("'", "''")

    q_sch_num = """
        SELECT esc.ogc_fid, esc.nombre, esc.direccion, esc.localidad,
               st_asgeojson(esc.wkb_geometry_4326) AS geojson,
               1 as score
        FROM escuelasutf8 esc
        WHERE esc.id_distrito = '%(distrito)s'
        AND esc.id_seccion = '%(seccion)s'
        AND esc.num_escuela = '%(var)s'
    """

    q_sim = """
        SELECT esc.ogc_fid, esc.nombre, esc.direccion, esc.localidad,
               st_asgeojson(esc.wkb_geometry_4326) AS geojson,
               similarity(%(key)s, '%(val)s') as score
        FROM escuelasutf8 esc
        WHERE esc.id_distrito = '%(distrito)s'
        AND esc.id_seccion = '%(seccion)s'
        AND similarity(%(key)s, '%(val)s') IS NOT NULL"""

    q_end = """ ORDER BY score DESC LIMIT 40"""

    q = q_sch_num % {'distrito': distrito_id, 'seccion': seccion_id, 'var': n}
    if search_type is not None:
        if search_type == "":
            q += ' UNION ' + q_sim % {'distrito': distrito_id,
                                      'seccion': seccion_id,
                                      'key': 'nombre',
                                      'val': nombre}

            q += ' UNION ' + q_sim % {'distrito': distrito_id,
                                      'seccion': seccion_id,
                                      'key': 'direccion',
                                      'val': direccion}
        elif search_type == "n":
            q += ' UNION ' + q_sim % {'distrito': distrito_id,
                                      'seccion': seccion_id,
                                      'key': 'nombre',
                                      'val': nombre}
        elif search_type == "a":
            q += ' UNION ' + q_sim % {'distrito': distrito_id,
                                      'seccion': seccion_id,
                                      'key': 'direccion',
                                      'val': direccion}
        elif search_type == "l":
            q += ' UNION ' + q_sim % {'distrito': distrito_id,
                                      'seccion': seccion_id,
                                      'key': 'localidad',
                                      'val': localidad}

    q = q + q_end

    r = [dict(e.items() + [('geojson', json.loads(e['geojson']))])
         for e in db.query(q)]

    return flask.Response(flask.json.dumps(r),
                          mimetype='application/json')


@app.route('/matches/<int:establecimiento_id>',
           methods=['DELETE'])
def match_delete(establecimiento_id):
    """ modificar los weighted_matches para un (establecimiento, escuela) """
    # borrar todos los matches humanos anteriores para un establecimiento
    q = DELETE_MATCHES_QUERY % (establecimiento_id)
    db.query(q)
    return flask.Response('')


@app.route('/matches/<int:establecimiento_id>/<int:place_id>',
           methods=['POST'])
def match_create(establecimiento_id, place_id):
    # asegurarse que el establecimiento y el lugar existan
    # y que el lugar este contenido dentro del distrito
    # del establecimiento
    q = """
        SELECT e.*
        FROM establecimientos e
        INNER JOIN escuelasutf8 esc
            ON esc.id_distrito = e.id_distrito
        WHERE e.id = %d
        AND esc.ogc_fid = %d """ % (establecimiento_id, place_id)

    if len(list(db.query(q))) == 0:
        abort(400)

    # crear un match para un (establecimiento, escuela) implica
    # borrar todos los matches humanos anteriores para dicho establecimiento
    q = DELETE_MATCHES_QUERY % (establecimiento_id)
    db.query(q)

    db['weighted_matches'].insert({
        'establecimiento_id': establecimiento_id,
        'escuela_id': place_id,
        'score': 1,
        'match_source': 1  # human
    })

    return flask.Response('')


@app.route('/create', methods=['POST'])
def create_place():
    """ crea un nuevo lugar (una 'escuela') """

    q = """
    INSERT INTO escuelasutf8 (nombre, direccion, localidad,
                              wkb_geometry_4326,
                              id_distrito, id_seccion)
    VALUES ('%s', '%s', '%s', '%s', '%s', '%s')
    RETURNING ogc_fid
    """ % (
        request.form['nombre'].replace("'", "''"),
        request.form['direccion'].replace("'", "''"),
        request.form['localidad'].replace("'", "''"),
        request.form['wkb_geometry_4326'],
        request.form['distrito'],
        request.form['seccion']
    )
    r = db.query(q)
    return flask.Response(flask.json.dumps(r.next()),
                          mimetype="application/json")


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('localhost', 8000, app, use_reloader=True)
