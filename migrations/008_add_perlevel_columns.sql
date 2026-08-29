ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS temp_600hpa    REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS geopot_700hpa  REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS geopot_600hpa  REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS wind_700hpa    REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS wind_600hpa    REAL;
ALTER TABLE weather_readings ADD COLUMN IF NOT EXISTS wind_500hpa    REAL;
