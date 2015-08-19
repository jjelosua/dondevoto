$(function(){
    map = new GMaps({
        div: '#map',
        lat: -12.043333,
        lng: -77.028333,
        mapType: google.maps.MapTypeId.HYBRID,
        mapTypeControlOptions: {
            mapTypeIds : ["hybrid", "roadmap", "satellite", "terrain", "osm"]
        },
        rightclick: function(e) {
            lastRightClickedPoint = e.latLng;
        }
    });

    map.addMapType("osm", {
        getTileUrl: function(coord, zoom) {
            return "http://otile1.mqcdn.com/tiles/1.0.0/map/" + zoom + "/" + coord.x + "/" + coord.y + ".png";
        },
        tileSize: new google.maps.Size(256, 256),
        name: "OpenStreetMap",
        maxZoom: 18
    });

    map.setContextMenu({
        control: 'map',
        options: [
            {
                title: 'Crear centro de votación aquí',
                name: 'agregar_lugar',
                action: function(e) {
                    var tr = $('tr.establecimiento.active');
                    var p_d = $('select#distrito option:selected').val().split('-');
                    var c = $('td', tr).map(function(d,e) { return e.innerHTML; });
                    if( $('tr.establecimiento.active + tr.matches td table tbody').length ) {
                      $('tr.establecimiento.active + tr.matches td table tbody').prepend(new_estab_tmpl({contents: c}));
                    }
                    else {
                      $('tr.establecimiento.active + tr.matches td table').prepend(new_estab_tmpl({contents: c}));  
                    }
                    var place_data = {
                        nombre: c[0],
                        direccion: c[1],
                        localidad: c[2],
                        wkb_geometry_4326: 'SRID=4326;POINT(' + lastRightClickedPoint.lng() + ' ' + lastRightClickedPoint.lat() + ')',
                        distrito: p_d[0],
                        seccion: p_d[1]
                    };
                    $.post('/create',
                           place_data,
                           function(d) {
                               place_data['ogc_fid'] = d['ogc_fid'];
                               var new_tr = $('tr.establecimiento.active + tr.matches td table tr:first-child');
                               new_tr.data('place', place_data);
                               $('input[type=checkbox]', new_tr)
                                   .prop('checked', true)
                                   .trigger('change');
                           });
                }
            },
        ]
    });

    var table_tmpl = _.template($('#establecimientos-template').html());
    var matches_tmpl = _.template($('#matches-template').html());
    var infowindow_tmpl = _.template($('#infowindow-template').html());
    var completion_tmpl = _.template($('#completion-template').html());
    var new_estab_tmpl = _.template($('#new-establecimiento-template').html());


    var polygon = null;
    var markers = [];

    var maxZoomService = new google.maps.MaxZoomService();

    var currentBounds = null;
    var currentMarker = null;
    var currentPlace  = null;
    var currentSeccion = null;
    var currentDistrito = null;
    var lastRightClickedPoint = null;

    var updateCompletion = function() {
        $.get('/completion', function(provincias) {
            $('#provincia-ranking').html(completion_tmpl({provincias:provincias}));
        })
    };

    completionRankingInterval = window.setInterval(updateCompletion, 10000);
    updateCompletion();

    var addGeocomplete = function(selector) {
        $(selector)
            .geocomplete({ bounds: polygon.getBounds() })
            .bind("geocode:result", function(event, result) {
                if (!polygon.getBounds().contains(result.geometry.location))
                    // no salir de los bounds actuales si el geocoder
                    // retorna algo afuera de esos bounds
                    return;
                maxZoomService.getMaxZoomAtLatLng(result.geometry.location, function(r) {
                    if (r.status == google.maps.MaxZoomStatus.OK)
                        map.setZoom(r.zoom);
                    map.map.panTo(result.geometry.location);
                });

            });
    };

    $('select#distrito').on('change', function() {
        var p_d = $(this).val().split('-');
        var provincia = $(this).parent('optgroup').attr('label')
        history.pushState({foo: null}, "", "/" + p_d[0] + "/" + p_d[1]);
        $.get('/establecimientos/' + p_d.join('/'),
              function(data) {
                  $('table#establecimientos')
                      .html(table_tmpl({establecimientos: data, provincia: p_d[0] }));
              });

        map.removeMarkers(markers);
        markers = [];

        currentSeccion = p_d[1];
        currentDistrito = p_d[0];

        $.get('/seccion/' + p_d.join('/'), function(data) {
            currentBounds = data.bounds.coordinates[0].map(function(p) {
                return new google.maps.LatLng(p[1], p[0]);
            });
            map.fitLatLngBounds(currentBounds);

            if (polygon != null) map.removePolygon(polygon);

            polygon = map.drawPolygon({
                paths: data.geojson.coordinates,
                useGeoJSON: true,
                strokeOpacity: 0.2,
                strokeWeight: 1,
                strokeColor: '#ff0000',
                fillColor: '#BBD8E9',
                fillOpacity: 0.4,
                clickable: false
            });

            $('a#shapefile').attr('href', '/shape/' + p_d[0] + '/' + p_d[1]);

        });
    });

    var showMarker = function(e) {
        console.log(e);
    };

    $(document).on({
      'click': function(e){
        e.preventDefault();
        var loc = $('input#latlng').val();
        var l_l = loc.split(',');
        var g = new google.maps.LatLng(l_l[0], l_l[1]);
        if (polygon.getBounds().contains(g)) {
          var tr = $('tr.establecimiento.active');
          var p_d = $('select#distrito option:selected').val().split('-');
          var c = $('td', tr).map(function(d,e) { return e.innerHTML; });
          if( $('tr.establecimiento.active + tr.matches td table tbody').length ) {
            $('tr.establecimiento.active + tr.matches td table tbody').prepend(new_estab_tmpl({contents: c}));
          }
          else {
            $('tr.establecimiento.active + tr.matches td table').prepend(new_estab_tmpl({contents: c}));  
          }
          var place_data = {
            nombre: c[0],
            direccion: c[1],
            localidad: c[2],
            wkb_geometry_4326: 'SRID=4326;POINT(' + l_l[1].trim() + ' ' + l_l[0].trim() + ')',
            distrito: p_d[0],
            seccion: p_d[1]
          };
          $.post('/create',place_data,
               function(d) {
                   place_data['ogc_fid'] = d['ogc_fid'];
                   var new_tr = $('tr.establecimiento.active + tr.matches td table tr:first-child');
                   new_tr.data('place', place_data);
                   $('input[type=checkbox]', new_tr)
                       .prop('checked', true)
                       .trigger('change');
          });
          $('input#latlng').val("");
        } 
        else {
          $('span#error').css('visibility', 'visible');
          $('input#latlng').val("");
          setTimeout(function(){$("span#error").css('visibility', 'hidden');}, 2000);
        } 
        return false;
      }
    }, 'button#latlngBut')


    $(document).on({
        'click': function() {
            if (currentMarker) {
                currentMarker.infoWindow.close();
            }
            var d = $(this).data('place');
            currentPlace = d;
            currentMarker = _.find(map.markers, function(m) {
                return m.details == d;
            });
            // Simulate a click on the actual marker
            google.maps.event.trigger(currentMarker, 'click');
        },
        'dblclick': function() {
            maxZoomService.getMaxZoomAtLatLng(currentMarker.getPosition(), function(r) {
                if (r.status == google.maps.MaxZoomStatus.OK)
                    map.setZoom(r.zoom);
                map.map.panTo(currentMarker.getPosition());
            });
        }
    }, 'tr.matches tr')

    $(document).on({
        'change': function() { // checkbox to choose a match
            var chk = $(this);

            var establecimiento_tr = chk
                .parents('.matches')
                .prev();

            var establecimiento = establecimiento_tr
                .data('establecimiento-id');

            currentPlace = chk
                .parents('tr:not(.matches)')
                .data('place');

            var url = '/matches/' + establecimiento + '/' + currentPlace.ogc_fid;

            if (chk.is(':checked')) {
                establecimiento_tr.removeClass('guessed');
                establecimiento_tr.addClass('matched');
                $.post(url);
            }
            else { //delete
                // indicar que no hay match sólo si no hay ningun
                // chkbox activado
                if (!$('input[type=checkbox]').is(':checked'))
                    establecimiento_tr.removeClass('matched');

                $.post(url, { _method: 'delete'});
            }
        },
    }, 'tr.matches tr input[type=checkbox]')

    $(document).on({
        'click': function(e) {
            var a = $(this);
            var t = a.data('searchType');
            var tr = a.parents('tr.matches');
            var prev = tr.prev();
            $.get('/places/' + currentDistrito + '/' + currentSeccion,
                  { // Add nombre and localidad to the mixture for the similarity
                    nombre: $('td:nth-child(1)', prev).html(),
                    direccion: $('td:nth-child(2)', prev).html(), 
                    localidad: $('td:nth-child(3)', prev).html(),
                    search_type: t},
                  function(data) {
                      tr.remove();
                      prev.after(matches_tmpl({
                          matches: data,
                          seccion: '',
                          distrito: ''
                      }));
                      $('tr', prev.next()).each(function(i, t) {
                          $(this).data('place', data[i]);
                      });
                      map.removeMarkers(markers);
                      markers = []
                      data.forEach(function(m) {
                          var marker = map.addMarker({
                              lat: m.geojson.coordinates[1],
                              lng: m.geojson.coordinates[0],
                              details: m,
                              infoWindow: {
                                  content: infowindow_tmpl({place: m})
                              },
                              click: showMarker,
                          });
                          markers.push(marker);
                      });
                      if (markers.length > 0) map.fitZoom();
                      addGeocomplete($('input#geocomplete', $($(prev).next())));
                  });
            e.preventDefault();
            return false;
        }
    }, 'a.view-all-places')


    $(document).on(
        {
            // click en establecimiento, abre los matches
            'click': function() {
                $('tr', $(this).parent()).removeClass('active');
                $('tr.matches').remove();
                var tr = $(this);
                tr.addClass('active');
                var eid = $(this).data('establecimiento-id');
                $.get('/matches/' + eid,
                      function(data) {
                          // todo este quilombo es para sacar los duplicados que vienen del join
                          data =
                              _.sortBy(
                                  _.map(
                                      _.pairs(
                                          _.groupBy(data,
                                                    function(d) {
                                                        return d.ogc_fid;
                                                    }, data)
                                      ), function(p) {
                                          return _.max(p[1],
                                                       function(d) {
                                                           return d.score;
                                                       });
                                      }),
                                  function(d) {
                                      return -d.score;
                                  });

                          tr.after(matches_tmpl({
                              matches: data,
                              seccion: $('select#distrito option:selected').html(),
                              distrito: $('select#distrito option:selected').parent().attr('label')
                          }));
                          $('tr', tr.next()).each(function(i, t) {
                              $(this).data('place', data[i]);
                          });

                          if (_.some(data, function(d) { return d.score == 1}))
                              tr.addClass('matched');

                          map.removeMarkers(markers);
                          markers = []
                          data.forEach(function(m) {
                              var marker = map.addMarker({
                                  lat: m.geojson.coordinates[1],
                                  lng: m.geojson.coordinates[0],
                                  details: m,
                                  infoWindow: {
                                      content: infowindow_tmpl({place: m})
                                  },
                                  click: showMarker,
                              });
                              markers.push(marker);
                          });
                          if (markers.length > 0) map.fitZoom();

                          addGeocomplete($('input#geocomplete', tr.next()));
                      });
            }
        }, 'table#establecimientos tr.establecimiento');

    $(document).on("ajaxSend", function(e, xhr, settings, exception)  {
        if (settings.url == '/completion') return;
        $('#loading').css('visibility', 'visible');
    });

    $(document).on("ajaxComplete", function(e, xhr, settings, exception)  {
        $('#loading').css('visibility', 'hidden');
    });

    $('select#distrito').trigger('change');

});
