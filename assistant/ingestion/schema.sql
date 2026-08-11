-- Schéma SQLite pour les données GTFS statiques.
--
-- Les horaires (arrival_secondes, departure_secondes) sont stockés en
-- nombre de secondes depuis minuit, PAS en "HH:MM:SS". Un départ à 0h30
-- vaut 88200 (24h30 en secondes) et non "00:30:00" : ça permet de trier
-- et comparer les horaires avec de simples MIN()/MAX()/ORDER BY, sans
-- traitement spécial pour les courses qui franchissent minuit.

CREATE TABLE agency (
    agency_id TEXT PRIMARY KEY,
    agency_name TEXT NOT NULL,
    agency_url TEXT,
    agency_phone TEXT
);

CREATE TABLE stops (
    stop_id TEXT PRIMARY KEY,
    stop_code TEXT,
    stop_name TEXT NOT NULL,
    stop_lat REAL NOT NULL,
    stop_lon REAL NOT NULL,
    location_type INTEGER NOT NULL DEFAULT 0,
    parent_station TEXT,
    wheelchair_boarding INTEGER,
    -- Commune déclarée par le GTFS source (extension Mecatran, pas un
    -- champ standard). Sert de référence pour Session B, où la vraie
    -- déduction géographique par coordonnées sera calculée.
    commune_gtfs TEXT
);

CREATE TABLE routes (
    route_id TEXT PRIMARY KEY,
    agency_id TEXT REFERENCES agency(agency_id),
    route_short_name TEXT NOT NULL,
    route_long_name TEXT,
    route_type INTEGER NOT NULL,
    direction0_name TEXT,
    direction1_name TEXT
);

CREATE TABLE trips (
    trip_id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL REFERENCES routes(route_id),
    service_id TEXT NOT NULL,
    trip_headsign TEXT,
    direction_id INTEGER
);

CREATE TABLE stop_times (
    trip_id TEXT NOT NULL REFERENCES trips(trip_id),
    stop_id TEXT NOT NULL REFERENCES stops(stop_id),
    stop_sequence INTEGER NOT NULL,
    arrival_secondes INTEGER NOT NULL,
    departure_secondes INTEGER NOT NULL,
    pickup_type INTEGER NOT NULL DEFAULT 0,
    drop_off_type INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (trip_id, stop_sequence)
);

CREATE TABLE calendar (
    service_id TEXT PRIMARY KEY,
    monday INTEGER NOT NULL,
    tuesday INTEGER NOT NULL,
    wednesday INTEGER NOT NULL,
    thursday INTEGER NOT NULL,
    friday INTEGER NOT NULL,
    saturday INTEGER NOT NULL,
    sunday INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    service_name TEXT
);

CREATE TABLE calendar_dates (
    service_id TEXT NOT NULL,
    date TEXT NOT NULL,
    exception_type INTEGER NOT NULL
);

-- Index pour les requêtes qu'on sait déjà vouloir faire :
-- "quelles courses passent par cet arrêt", "quelles courses sur cette ligne".
CREATE INDEX idx_stop_times_stop_id ON stop_times(stop_id);
CREATE INDEX idx_stop_times_trip_id ON stop_times(trip_id);
CREATE INDEX idx_trips_route_id ON trips(route_id);
CREATE INDEX idx_stops_stop_name ON stops(stop_name);
