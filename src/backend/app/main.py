import ee
from google.auth import compute_engine
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI()

origins = [
    "http://earth.google.com",
    "https://earth.google.com",
    "http://storage.googleapis.com",
    "https://storage.googleapis.com",
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EE_API_ROOT = 'https://earthengine.googleapis.com/v1'

def _get_auth():
    scopes = [
        "https://www.googleapis.com/auth/earthengine"
    ]
    credentials = compute_engine.Credentials(scopes=scopes)

    return credentials

def _get_ee_map():
    # here is where you add you actual Earth Engine code/algorithm
    credentials = _get_auth()

    ee.Initialize(credentials)

    images = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    )

    stop = ee.Date('2023-02-01')
    start = stop.advance(-1, 'month')

    doyStop = stop.getRelative('day', 'year')
    doyStart = start.getRelative('day', 'year')

    # mean
    imagesMean = (
        images
        .filterDate('2018-01-01', '2023-01-01')
        .filter(ee.Filter.dayOfYear(doyStart, doyStop))
    )

    imagesMeanASC = (
        imagesMean
        .filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))
        .select([0, 1], ['b1_mean', 'b2_mean'])
        .mean()
    )

    imagesMeanDSC = (
        imagesMean
        .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
        .select([0, 1], ['b1_mean', 'b2_mean'])
        .mean()
    )

    # last
    imagesLast = images.filterDate(start, stop)

    imagesLastASC = (
        imagesLast
        .filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))
        .reduce(ee.Reducer.percentile([1]))
        .select([0, 1], ['b1', 'b2'])
    )

    imagesLastDSC = (
        imagesLast
        .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
        .reduce(ee.Reducer.percentile([1]))
        .select([0, 1], ['b1', 'b2'])
    )

    anomaly = (
        imagesLastASC
        .addBands(imagesMeanASC)
        .add(
            imagesLastDSC.addBands(imagesMeanDSC)
        )
        .divide(2)
    )

    flood = (
        imagesMeanASC
        .select('b1_mean')
        .subtract(imagesLastASC.select('b1'))
        .unitScale(6, 15)
    )
    
    map_result = flood.selfMask().getMapId({'palette': ['cyan']})
    logging.info(map_result)

    return map_result

CACHED_MAP_ID = None
CACHED_MAP_TIMESTAMP = None
CACHED_MAP_MAX_AGE = timedelta(hours=3)

def _get_ee_map_cached():
 """Wrap the actual EE code in caching."""
 global CACHED_MAP_ID
 global CACHED_MAP_TIMESTAMP
 now = datetime.utcnow()
 if (CACHED_MAP_ID is None) or ((now - CACHED_MAP_TIMESTAMP) > CACHED_MAP_MAX_AGE):
   CACHED_MAP_ID = _get_ee_map()
   CACHED_MAP_TIMESTAMP = now
 return CACHED_MAP_ID


@app.get("/get-map")
def get_map(x, y, z):
    """entrypoint to request the ee computation result tiles"""
    try:
        mapinfo = _get_ee_map_cached()
        mapid = mapinfo['mapid']
        return RedirectResponse(
            f"{EE_API_ROOT}/{mapid}/tiles/{int(z)}/{int(x)}/{int(y)}",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=repr(e))
