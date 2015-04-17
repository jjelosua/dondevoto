# coding: utf-8
from collections import OrderedDict
from subprocess import call
import zipfile, tempfile

import os
import re
import dataset
import flask
from flask import Flask, render_template, jsonify, abort, request, send_file
from werkzeug import Request
from werkzeug.contrib.fixers import ProxyFix
from wsgiauth import basic
import simplejson

# Umbral para considerar válidas a los matches calculados por el algoritmo
MATCH_THRESHOLD = 0.95
DELETE_MATCHES_QUERY = """ DELETE
                           FROM weighted_matches
                           WHERE establecimiento_id = %d
                             AND match_source = 1 """

from werkzeug.formparser import parse_form_data
from werkzeug.wsgi import get_input_stream
from io import BytesIO

OGR2OGR_PATH = os.environ.get('OGR2OGR_PATH', '/usr/local/bin/ogr2ogr')
GDAL_DATA = os.environ.get('GDAL_DATA', '/usr/local/Cellar/gdal/1.11.1_3/share/gdal/')

def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file), arcname=file)

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
app.wsgi_app = basic.basic('dondevoto', authfunc)(MethodMiddleware(app.wsgi_app))
app.wsgi_app = ProxyFix(app.wsgi_app)

db = dataset.connect('postgresql://jjelosua@localhost:5432/elecciones2013')

def provincias_distritos():
    """ mapa distrito -> [seccion, ..., seccion] """

    rv = OrderedDict()
    q = """
            SELECT da.dne_distrito_id,
                   da.provincia,
                   da.dne_seccion_id,
                   da.departamento,
                   count(e.*) AS estab_count,
                   count(wm.*) AS matches_count
            FROM divisiones_administrativas da
            INNER JOIN establecimientos e
               ON e.dne_distrito_id = da.dne_distrito_id
               AND e.dne_seccion_id = da.dne_seccion_id
            LEFT OUTER JOIN weighted_matches wm
               ON wm.establecimiento_id = e.id AND wm.score = 1 AND match_source = 1
            GROUP BY da.dne_distrito_id,
                     da.provincia,
                     da.dne_seccion_id,
                     da.departamento
            ORDER BY provincia,
                     departamento
        """
    for d in db.query(q):
        k = (d['dne_distrito_id'], d['provincia'],)
        if k not in rv:
            rv[k] = []
        rv[k].append((
            d['dne_distrito_id'],
            d['dne_seccion_id'],
            d['departamento'],
            d['estab_count'],
            d['matches_count']))

    return rv

@app.route("/")
@app.route("/<int:dne_distrito_id>/<int:dne_seccion_id>")
def index(dne_distrito_id=None, dne_seccion_id=None):
    return render_template('index.html',
                           provincias_distritos=provincias_distritos(),
                           dne_distrito_id=dne_distrito_id,
                           dne_seccion_id=dne_seccion_id)

# los ST_Scale que hay por todos lados son efectivamente una grasada
# pero las geometrias de divisiones administrativas no son buenas y a veces
# algunas escuelas quedaban afuera del st_within
# por eso, las agrando un poco antes de usuarlas como filtro :)


@app.route("/completion")
def completion():
    q = """ SELECT da.provincia,
                   count(e.*) AS estab_count,
                   count(wm.*) AS matches_count
            FROM divisiones_administrativas da
            INNER JOIN establecimientos e
               ON e.dne_distrito_id = da.dne_distrito_id
               AND e.dne_seccion_id = da.dne_seccion_id
            LEFT OUTER JOIN weighted_matches wm
               ON wm.establecimiento_id = e.id AND wm.score = 1 AND match_source = 1
            GROUP BY da.provincia
            ORDER BY provincia """

    return flask.Response(flask.json.dumps(list(db.query(q))),
                          mimetype='application/json')

@app.route("/seccion/<int:distrito_id>/<int:seccion_id>")
def seccion_info(distrito_id, seccion_id):
    q = """ SELECT *,
                   st_asgeojson(st_setsrid(ST_Translate(ST_Scale(wkb_geometry, 1.1, 1.1), ST_X(ST_Centroid(wkb_geometry))*(1 - 1.1), ST_Y(ST_Centroid(wkb_geometry))*(1 - 1.1) ), 900913)) AS geojson,
                   st_asgeojson(st_envelope(ST_Translate(ST_Scale(wkb_geometry, 1.1, 1.1), ST_X(ST_Centroid(wkb_geometry))*(1 - 1.1), ST_Y(ST_Centroid(wkb_geometry))*(1 - 1.1) ))) AS bounds
            FROM divisiones_administrativas
            WHERE dne_distrito_id = %d
              AND dne_seccion_id = %d """ % (distrito_id, seccion_id)

    r = [dict(e.items() + [('geojson',simplejson.loads(e['geojson'])),('wkb_geometry', ''), ('bounds',simplejson.loads(e['bounds']))])
         for e in db.query(q)][0]

    return flask.Response(flask.json.dumps(r),
                          mimetype='application/json')


@app.route("/establecimientos/<int:distrito_id>/<int:seccion_id>")
def establecimientos_by_distrito_and_seccion(distrito_id, seccion_id):
    q = """ SELECT e.id, e.establecimiento, e.direccion, e.localidad, e.circuito, 
            count(CASE WHEN wm.score >= 1 then 1 end) AS match_count,
            count(CASE WHEN wm.score < 1 AND wm.score >= 0.95 Then 1 end) AS guess_count
            FROM establecimientos e
            LEFT OUTER JOIN weighted_matches wm
               ON wm.establecimiento_id = e.id AND wm.score >= %f
            WHERE dne_distrito_id = %d
              AND dne_seccion_id = %d
            GROUP BY e.id, e.establecimiento, e.direccion, e.localidad, e.circuito
            ORDER BY e.circuito """ % (MATCH_THRESHOLD, distrito_id, seccion_id)

    return flask.Response(flask.json.dumps(list(db.query(q))),
                          mimetype='application/json')



@app.route("/matches/<int:establecimiento_id>", methods=['GET'])
def matched_escuelas(establecimiento_id):
    """ obtener los matches para un establecimiento """

    q = """
       SELECT wm.score,
       wm.establecimiento_id,
       esc.*,
       st_asgeojson(wkb_geometry_4326) AS geojson,
       (CASE WHEN wm.match_source >= 1 THEN 1
             WHEN wm.score > %f AND wm.match_source = 0 THEN 1
             ELSE 0
        END) AS is_match
       FROM weighted_matches wm
       INNER JOIN establecimientos e ON e.id = wm.establecimiento_id
       INNER JOIN escuelasutf8 esc ON esc.ogc_fid = wm.escuela_id
       WHERE wm.establecimiento_id = %d
       ORDER BY wm.score DESC
       """ % (MATCH_THRESHOLD, establecimiento_id)

    r = [dict(e.items() + [('geojson',simplejson.loads(e['geojson']))])
         for e in db.query(q)]

    return flask.Response(flask.json.dumps(r),
                          mimetype='application/json')

@app.route("/places/<int:distrito_id>/<int:seccion_id>")
def places_for_distrito_and_seccion(distrito_id, seccion_id):
    """ Todos los places (escuelas) para este distrito y seccion """
    # Add school number search on top
    extract_integer = re.compile(r"^.*?(\d+)").match
    match = extract_integer(request.args.get('nombre'))
    if match: 
      n = int(match.group(1))
    else:
      n = -1
    print n

    search_type = request.args.get('search_type')
    nombre = request.args.get('nombre').replace("'", "''")
    direccion = request.args.get('direccion').replace("'", "''")
    localidad = request.args.get('localidad').replace("'", "''")

    q_sch_num = """SELECT esc.ogc_fid, esc.nombre, esc.ndomiciio, esc.localidad,
                   st_asgeojson(wkb_geometry_4326) AS geojson,
                   1 as score
            FROM escuelasutf8 esc
            WHERE esc.dne_distrito_id = %(distrito)d
              AND esc.dne_seccion_id = %(seccion)d
              AND esc.school_number = %(var)s""" 


    q_sim = """ SELECT esc.ogc_fid, esc.nombre, esc.ndomiciio, esc.localidad,
                   st_asgeojson(wkb_geometry_4326) AS geojson,
                   similarity(%(key)s, '%(val)s') as score
            FROM escuelasutf8 esc
            WHERE esc.dne_distrito_id = %(distrito)d
              AND esc.dne_seccion_id = %(seccion)d
              AND similarity(%(key)s, '%(val)s') IS NOT NULL"""

    q_end = """ ORDER BY score DESC
            LIMIT 30"""

    q = q_sch_num % {'distrito': distrito_id, 'seccion': seccion_id, 'var': n}
    if search_type is not None:
      if search_type == "":
        q = q + ' UNION ' + q_sim % {'distrito': distrito_id, 'seccion': seccion_id, 
                                     'key': 'nombre', 'val': nombre}
        q = q + ' UNION ' + q_sim % {'distrito': distrito_id, 'seccion': seccion_id,
                                     'key': 'ndomiciio', 'val': direccion}
      elif search_type == "n":
        q = q + ' UNION ' + q_sim % {'distrito': distrito_id, 'seccion': seccion_id,
                                     'key': 'nombre', 'val': nombre}
      elif search_type == "a":
        q = q + ' UNION ' + q_sim % {'distrito': distrito_id, 'seccion': seccion_id,
                                     'key': 'ndomiciio', 'val': direccion}
      elif search_type == "l":
        q = q + ' UNION ' + q_sim % {'distrito': distrito_id, 'seccion': seccion_id, 
                                     'key': 'localidad', 'val': localidad}
    q = q + q_end

    r = [dict(e.items() + [('geojson',simplejson.loads(e['geojson']))])
         for e in db.query(q)]

    return flask.Response(flask.json.dumps(r),
                          mimetype='application/json')

@app.route('/matches/<int:establecimiento_id>/<int:place_id>',
           methods=['DELETE'])
def match_delete(establecimiento_id, place_id):
    """ modificar los weighted_matches para un (establecimiento, escuela) """
    # borrar todos los matches humanos anteriores para un establecimiento
    q = DELETE_MATCHES_QUERY % (establecimiento_id)
    db.query(q)
    return flask.Response('')


@app.route('/matches/<int:establecimiento_id>/<int:place_id>', methods=['POST'])
def match_create(establecimiento_id, place_id):
    # asegurarse que el establecimiento y el lugar existan
    # y que el lugar este contenido dentro del distrito
    # del establecimiento
    q = """ SELECT e.*
            FROM establecimientos e
            INNER JOIN escuelasutf8 esc 
            ON esc.dne_distrito_id = e.dne_distrito_id
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
        'match_source': 1 # human
    })

    return flask.Response('')

@app.route('/create', methods=['POST'])
def create_place():
    """ crea un nuevo lugar (una 'escuela') """

    q = """
    INSERT INTO escuelasutf8 (nombre, ndomiciio, localidad, wkb_geometry_4326, dne_distrito_id, dne_seccion_id)
    VALUES ('%s', '%s', '%s', '%s', %s, %s)
    RETURNING ogc_fid
    """ % (
        request.form['nombre'].replace("'", "''"),
        request.form['ndomiciio'].replace("'", "''"),
        request.form['localidad'].replace("'", "''"),
        request.form['wkb_geometry_4326'],
        request.form['distrito'],
        request.form['seccion']
    )
    r = db.query(q)
    return flask.Response(flask.json.dumps(r.next()),
                          mimetype="application/json")

@app.route('/shape/<int:dne_distrito_id>')
@app.route('/shape/<int:dne_distrito_id>/<int:dne_seccion_id>')
def get_shapefile(dne_distrito_id, dne_seccion_id=None):
    q_no_seccion = """
                  SELECT distinct(e.*),
                         esc.wkb_geometry_4326,
                         wm.score
                  FROM establecimientos e
                  INNER JOIN weighted_matches wm ON wm.establecimiento_id = e.id
                  INNER JOIN escuelasutf8 esc ON wm.escuela_id = esc.ogc_fid
                  WHERE e.dne_distrito_id = %s
                    AND (wm.match_source >= 1
                         OR (wm.match_source = 0
                             AND wm.score >= %f))
                  ORDER BY e.circuito, wm.score
                  """

    q_seccion = """
                  SELECT distinct(e.*),
                         esc.wkb_geometry_4326,
                         wm.score
                  FROM establecimientos e
                  INNER JOIN weighted_matches wm ON wm.establecimiento_id = e.id
                  INNER JOIN escuelasutf8 esc ON wm.escuela_id = esc.ogc_fid
                  WHERE e.dne_distrito_id = %s
                    AND e.dne_seccion_id = %d
                    AND (wm.match_source >= 1
                         OR (wm.match_source = 0
                             AND wm.score >= %f))
                  ORDER BY e.circuito, wm.score
                  """

    if dne_seccion_id is not None:
        q = q_seccion % (dne_distrito_id, dne_seccion_id, MATCH_THRESHOLD)
    else:
        q = q_no_seccion % (dne_distrito_id, MATCH_THRESHOLD)
        dne_seccion_id = 0

    tmp_dir = tempfile.mkdtemp()

    os.environ['GDAL_DATA'] = GDAL_DATA
    # ojo con el injection aca. Si lo usas en algun lado, fijate que onda.
    call("%s -f \"ESRI Shapefile\" -a_srs EPSG:4326 %s.shp PG:\"host=localhost user=jjelosua dbname=elecciones2013\" -sql \"%s\"" \
         % (OGR2OGR_PATH,
            os.path.join(tmp_dir, "%s-%s.shp" % (dne_distrito_id, dne_seccion_id)),
            q),
         shell=True)

    zip_path = '/tmp/%s-%s.zip' % (dne_distrito_id, dne_seccion_id)
    zip = zipfile.ZipFile(zip_path, 'w')
    zipdir(tmp_dir, zip)
    zip.close()

    return send_file(zip_path, mimetype='application/zip', as_attachment=True)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('localhost', 8000, app, use_reloader=True)
