SAMPLE_RAW_FIRMS_RECORDS = [
    # 1. Normal Thermal Observation (VIIRS NOAA-20)
    {
        "latitude": 21.6852,
        "longitude": 72.5753,
        "bright_ti4": 348.2,
        "scan": 0.38,
        "track": 0.37,
        "acq_date": "2026-08-30",
        "acq_time": "0845",
        "satellite": "N",
        "confidence": "h",
        "version": "1.0NRT",
        "bright_ti5": 298.4,
        "frp": 84.6,
        "daynight": "N"
    },
    # 2. High-FRP Observation (Jamnagar Flare - Suomi-NPP)
    {
        "latitude": 22.3880,
        "longitude": 69.8320,
        "bright_ti4": 365.4,
        "scan": 0.40,
        "track": 0.38,
        "acq_date": "2026-08-30",
        "acq_time": "0915",
        "satellite": "NPP",
        "confidence": "h",
        "version": "1.0NRT",
        "bright_ti5": 305.1,
        "frp": 320.0,
        "daynight": "N"
    },
    # 3. Low-Confidence / Agricultural Observation (Punjab - MODIS Terra)
    {
        "latitude": 30.9000,
        "longitude": 75.8500,
        "brightness": 315.2,
        "scan": 1.2,
        "track": 1.1,
        "acq_date": "2026-08-30",
        "acq_time": "1030",
        "satellite": "T",
        "confidence": 28,
        "version": "6.1NRT",
        "bright_t31": 290.0,
        "frp": 8.4,
        "daynight": "D"
    },
    # 4. Duplicate of #1 (Should be deduplicated)
    {
        "latitude": 21.6852,
        "longitude": 72.5753,
        "bright_ti4": 348.2,
        "scan": 0.38,
        "track": 0.37,
        "acq_date": "2026-08-30",
        "acq_time": "0845",
        "satellite": "NOAA-20",
        "confidence": "h",
        "version": "1.0NRT",
        "bright_ti5": 298.4,
        "frp": 84.6,
        "daynight": "N"
    },
    # 5. Invalid Coordinate Record (Latitude 125.0 > 90.0) -> Rejection
    {
        "latitude": 125.0,
        "longitude": 72.5753,
        "bright_ti4": 340.0,
        "acq_date": "2026-08-30",
        "acq_time": "0845",
        "satellite": "NOAA-20",
        "confidence": "nominal",
        "frp": 25.0,
        "daynight": "D"
    },
    # 6. Negative FRP Record -> Clamping & Warning Flag
    {
        "latitude": 21.1210,
        "longitude": 72.6450,
        "bright_ti4": 335.0,
        "acq_date": "2026-08-30",
        "acq_time": "0900",
        "satellite": "21",
        "confidence": "n",
        "frp": -5.0,
        "daynight": "D"
    },
    # 7. MODIS Aqua Day Observation (Jamshedpur Steel)
    {
        "latitude": 22.8020,
        "longitude": 86.2030,
        "brightness": 334.2,
        "scan": 1.0,
        "track": 1.0,
        "acq_date": "2026-08-30",
        "acq_time": "0745",
        "satellite": "A",
        "confidence": 88,
        "version": "6.1NRT",
        "frp": 39.5,
        "daynight": "D"
    }
]
