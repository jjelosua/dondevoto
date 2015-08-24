--EXTENSIONS

-- Extension: pg_trgm
-- DROP EXTENSION pg_trgm;
 CREATE EXTENSION IF NOT EXISTS pg_trgm
  SCHEMA public
  VERSION "1.1";

-- Extension: plpgsql
-- DROP EXTENSION plpgsql;
 CREATE EXTENSION IF NOT EXISTS plpgsql
  SCHEMA pg_catalog
  VERSION "1.0";

-- Extension: postgis
-- DROP EXTENSION postgis;
 CREATE EXTENSION IF NOT EXISTS postgis
  SCHEMA public
  VERSION "2.1.7";


--TABLES AND INDEXES

-- Table: divisiones_administrativas
CREATE TABLE divisiones_administrativas
(
  ogc_fid integer NOT NULL,
  id_distrito character varying(2) NOT NULL,
  desc_distrito character varying(80), 
  id_seccion character varying(3) NOT NULL,
  desc_seccion character varying(80),
  wkb_geometry_4326 geometry(Geometry,4326),
  CONSTRAINT divisiones_administrativas_pk PRIMARY KEY (ogc_fid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE divisiones_administrativas
  OWNER TO jjelosua;

-- Index: divisiones_administrativas_geom_idx

DROP INDEX IF EXISTS divisiones_administrativas_geom_idx;
CREATE INDEX divisiones_administrativas_geom_idx
  ON divisiones_administrativas
  USING gist
  (wkb_geometry_4326);


-- Table: establecimientos
DROP TABLE IF EXISTS establecimientos;
CREATE TABLE establecimientos
(
  id integer,
  id_distrito character varying(2) NOT NULL,
  id_seccion character varying(3) NOT NULL,
  id_dpto character varying(5) NOT NULL,
  desc_seccion text,
  id_circuito character varying(5) NOT NULL,
  nombre text,
  direccion text,
  localidad text,
  cod_postal character varying(10),
  num_escuela character varying(10),
  cod_SIE text,
  latitud character varying(50),
  longitud character varying(50),
  wkb_geometry_4326 geometry(Point,4326),
  CONSTRAINT establecimientos_pk PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE establecimientos
  OWNER TO jjelosua;

-- Index: escuelasutf8_geom_idx
DROP INDEX IF EXISTS establecimientos_geom_idx;
CREATE INDEX establecimientos_geom_idx
  ON establecimientos
  USING gist
  (wkb_geometry_4326);


-- Table: escuelasutf8
DROP TABLE IF EXISTS escuelasutf8;
CREATE TABLE escuelasutf8
(
  ogc_fid serial NOT NULL,
  id_distrito character varying(2) NOT NULL,
  id_seccion character varying(3) NOT NULL,
  nombre character varying(80),
  direccion character varying(80),
  localidad character varying(80),
  cod_postal character varying(80),
  num_escuela character varying(10),
  cueanexo character varying(80),
  wkb_geometry_4326 geometry(Point,4326),
  CONSTRAINT escuelasutf8_pk PRIMARY KEY (ogc_fid)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE escuelasutf8
  OWNER TO jjelosua;

-- Index: escuelasutf8_geom_idx
DROP INDEX IF EXISTS escuelasutf8_geom_idx;
CREATE INDEX escuelasutf8_geom_idx
  ON escuelasutf8
  USING gist
  (wkb_geometry_4326);


-- Table: dedupe_matches
DROP TABLE IF EXISTS dedupe_matches;
CREATE TABLE dedupe_matches
(
  id serial NOT NULL,
  establecimiento_id integer,
  escuela_id integer,
  the_geom geometry(Point,4326),
  match_source smallint,
  score double precision,
  CONSTRAINT dedupe_matches_pk PRIMARY KEY (id),
  CONSTRAINT matches_escuela_fk FOREIGN KEY (escuela_id)
      REFERENCES escuelasutf8 (ogc_fid) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT matches_establecimiento_fk FOREIGN KEY (establecimiento_id)
      REFERENCES establecimientos (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION
)
WITH (
  OIDS=FALSE
);
ALTER TABLE dedupe_matches
  OWNER TO jjelosua;


-- Table: weighted_matches
DROP TABLE IF EXISTS weighted_matches;
CREATE TABLE weighted_matches
(
  id serial NOT NULL,
  establecimiento_id integer,
  escuela_id integer,
  score double precision,
  match_source smallint,
  CONSTRAINT weighted_matches_pk PRIMARY KEY (id),
  CONSTRAINT matches_escuela_fk FOREIGN KEY (escuela_id)
      REFERENCES escuelasutf8 (ogc_fid) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT matches_establecimiento_fk FOREIGN KEY (establecimiento_id)
      REFERENCES establecimientos (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION
)
WITH (
  OIDS=FALSE
);
ALTER TABLE weighted_matches
  OWNER TO jjelosua;