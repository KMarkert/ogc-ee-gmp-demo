/**
 * @license
 * Copyright 2023 Google LLC. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
// import { GeoJsonLayer } from "https://cdn.skypack.dev/deck.gl";
// import { GoogleMapsOverlay } from "https://cdn.skypack.dev/@deck.gl/google-maps";
const GeoJsonLayer = deck.GeoJsonLayer;
const BitmapLayer = deck.BitmapLayer;
const TileLayer = deck.TileLayer;
const GoogleMapsOverlay = deck.GoogleMapsOverlay;

// Initialize and add the map
async function initMap() {
  const response = await fetch('config.json');
  const config = await response.json();

  const map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 38.5, lng: -121.7 },
    zoom: 11,
  });
  const deckOverlay = new GoogleMapsOverlay({
    layers: [
      new TileLayer({
        // https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Tile_servers
        // data: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
        data: config.data_endpoint,
    
        minZoom: 1,
        maxZoom: 13,
        tileSize: 256,

        onTileLoad: () => {
          /* eslint-disable no-undef */
          // @ts-ignore defined in include
          progress.done(); // hides progress bar
          /* eslint-enable no-undef */
        },
    
        renderSubLayers: props => {
          const {
            bbox: {west, south, east, north}
          } = props.tile;
    
          return new BitmapLayer(props, {
            data: null,
            image: props.data,
            bounds: [west, south, east, north]
          });
        }
      })
    ],
  });

  deckOverlay.setMap(map);
}

window.initMap = initMap;