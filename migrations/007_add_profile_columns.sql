ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS temp_700hpa    REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS geopot_850hpa  REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS geopot_500hpa  REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS wind_850hpa    REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS rh_850hpa      REAL;
