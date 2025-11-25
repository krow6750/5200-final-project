-- CS2 esports relational schema and seed data
-- Run with: psql -f chen_final_project.sql

-- Clean slate for iterative development
DROP TABLE IF EXISTS map_pool_history CASCADE;
DROP TABLE IF EXISTS team_roster CASCADE;
DROP TABLE IF EXISTS tournament_results CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS players CASCADE;
DROP TABLE IF EXISTS maps CASCADE;
DROP TABLE IF EXISTS tournaments CASCADE;
DROP TABLE IF EXISTS teams CASCADE;

-- Core reference data
CREATE TABLE teams (
    team_id     SERIAL PRIMARY KEY,
    team_name   VARCHAR(80) NOT NULL UNIQUE,
    region      VARCHAR(40) NOT NULL,
    founded_year SMALLINT,
    CONSTRAINT team_region_chk CHECK (region <> '')
);

CREATE TABLE players (
    player_id   SERIAL PRIMARY KEY,
    player_name VARCHAR(80) NOT NULL,
    country     VARCHAR(60),
    role        VARCHAR(40),
    team_id     INTEGER REFERENCES teams(team_id) ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT player_name_chk CHECK (player_name <> '')
);

CREATE TABLE tournaments (
    tournament_id SERIAL PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    organizer     VARCHAR(80),
    prize_pool    NUMERIC(12,2) DEFAULT 0 CHECK (prize_pool >= 0),
    start_date    DATE,
    end_date      DATE,
    location      VARCHAR(120),
    CONSTRAINT tournament_dates_chk CHECK (start_date IS NULL OR end_date IS NULL OR start_date <= end_date)
);

CREATE TABLE maps (
    map_id    SERIAL PRIMARY KEY,
    map_name  VARCHAR(60) NOT NULL UNIQUE
);

-- Track map pool rotations over time (active/reserve/retired)
CREATE TABLE map_pool_history (
    pool_id    SERIAL PRIMARY KEY,
    map_id     INTEGER NOT NULL REFERENCES maps(map_id) ON UPDATE CASCADE ON DELETE CASCADE,
    status     VARCHAR(20) NOT NULL CHECK (status IN ('active', 'reserve', 'retired')),
    valid_from DATE NOT NULL,
    valid_to   DATE,
    CONSTRAINT map_pool_dates_chk CHECK (valid_to IS NULL OR valid_from <= valid_to)
);

CREATE TABLE matches (
    match_id        SERIAL PRIMARY KEY,
    tournament_id   INTEGER NOT NULL REFERENCES tournaments(tournament_id) ON UPDATE CASCADE ON DELETE CASCADE,
    team1_id        INTEGER NOT NULL REFERENCES teams(team_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    team2_id        INTEGER NOT NULL REFERENCES teams(team_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    winner_team_id  INTEGER REFERENCES teams(team_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    map_id          INTEGER REFERENCES maps(map_id) ON UPDATE CASCADE ON DELETE SET NULL,
    match_date      DATE,
    best_of         SMALLINT DEFAULT 1 CHECK (best_of > 0),
    team1_score     SMALLINT DEFAULT 0 CHECK (team1_score >= 0),
    team2_score     SMALLINT DEFAULT 0 CHECK (team2_score >= 0),
    CONSTRAINT different_teams_chk CHECK (team1_id <> team2_id),
    CONSTRAINT winner_valid_chk CHECK (winner_team_id IS NULL OR winner_team_id IN (team1_id, team2_id))
);

CREATE TABLE tournament_results (
    result_id     SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(tournament_id) ON UPDATE CASCADE ON DELETE CASCADE,
    team_id       INTEGER NOT NULL REFERENCES teams(team_id) ON UPDATE CASCADE ON DELETE CASCADE,
    placement     SMALLINT NOT NULL CHECK (placement > 0),
    earnings      NUMERIC(12,2) DEFAULT 0 CHECK (earnings >= 0),
    UNIQUE (tournament_id, team_id),
    UNIQUE (tournament_id, placement)
);

-- Roster history with active flag; trigger below enforces max 5 active per team
CREATE TABLE team_roster (
    roster_id  SERIAL PRIMARY KEY,
    team_id    INTEGER NOT NULL REFERENCES teams(team_id) ON UPDATE CASCADE ON DELETE CASCADE,
    player_id  INTEGER NOT NULL REFERENCES players(player_id) ON UPDATE CASCADE ON DELETE CASCADE,
    is_active  BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date   DATE,
    UNIQUE (team_id, player_id),
    CONSTRAINT roster_dates_chk CHECK (end_date IS NULL OR start_date IS NULL OR start_date <= end_date)
);

-- Enforce max 5 active players per team
CREATE OR REPLACE FUNCTION enforce_active_roster_limit() RETURNS trigger AS $$
DECLARE
    active_count INTEGER;
BEGIN
    IF NEW.is_active THEN
        SELECT COUNT(*) INTO active_count
        FROM team_roster r
        WHERE r.team_id = NEW.team_id
          AND r.is_active
          AND (TG_OP <> 'UPDATE' OR r.roster_id <> COALESCE(OLD.roster_id, -1));

        IF active_count >= 5 THEN
            RAISE EXCEPTION 'Cannot exceed 5 active players for team %', NEW.team_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_active_roster_cap
BEFORE INSERT OR UPDATE ON team_roster
FOR EACH ROW
EXECUTE FUNCTION enforce_active_roster_limit();

-- Useful secondary indexes
CREATE INDEX idx_players_team ON players(team_id);
CREATE INDEX idx_matches_tournament ON matches(tournament_id);
CREATE INDEX idx_matches_map ON matches(map_id);
CREATE INDEX idx_results_tournament ON tournament_results(tournament_id);
CREATE INDEX idx_roster_team ON team_roster(team_id);
CREATE INDEX idx_roster_player ON team_roster(player_id);
CREATE INDEX idx_pool_map ON map_pool_history(map_id);

-- Seed data for development/demo
INSERT INTO teams (team_name, region, founded_year) VALUES
    ('G2 Esports', 'EU', 2013),
    ('Natus Vincere', 'CIS', 2009),
    ('FaZe Clan', 'EU', 2010),
    ('Team Vitality', 'EU', 2013);

INSERT INTO players (player_name, country, role, team_id) VALUES
    ('m0NESY', 'Russia', 'AWPer', 1),
    ('NiKo', 'Bosnia', 'Rifler', 1),
    ('s1mple', 'Ukraine', 'AWPer', 2),
    ('b1t', 'Ukraine', 'Rifler', 2),
    ('ropz', 'Estonia', 'Rifler', 3),
    ('broky', 'Latvia', 'AWPer', 3),
    ('ZywOo', 'France', 'AWPer', 4),
    ('apEX', 'France', 'IGL', 4);

INSERT INTO tournaments (name, organizer, prize_pool, start_date, end_date, location) VALUES
    ('IEM Cologne 2024', 'ESL', 1000000, '2024-08-10', '2024-08-18', 'Cologne, Germany'),
    ('PGL Major Copenhagen 2024', 'PGL', 1250000, '2024-03-17', '2024-03-31', 'Copenhagen, Denmark');

-- Late-2025 active duty pool (Mirage, Inferno, Nuke, Overpass, Vertigo, Ancient, Dust2); Anubis retained for history
INSERT INTO maps (map_name) VALUES
    ('Mirage'),
    ('Inferno'),
    ('Nuke'),
    ('Overpass'),
    ('Vertigo'),
    ('Ancient'),
    ('Dust2'),
    ('Anubis');

INSERT INTO map_pool_history (map_id, status, valid_from, valid_to) VALUES
    (1, 'active', '2025-02-01', NULL),  -- Mirage
    (2, 'active', '2025-02-01', NULL),  -- Inferno
    (3, 'active', '2025-02-01', NULL),  -- Nuke
    (4, 'active', '2025-02-01', NULL),  -- Overpass
    (5, 'active', '2025-02-01', NULL),  -- Vertigo
    (6, 'active', '2025-02-01', NULL),  -- Ancient
    (7, 'active', '2025-02-01', NULL),  -- Dust2
    (8, 'retired', '2023-09-27', '2025-02-01'); -- Anubis historical

INSERT INTO matches (tournament_id, team1_id, team2_id, winner_team_id, map_id, match_date, best_of, team1_score, team2_score) VALUES
    (1, 1, 3, 3, 3, '2024-08-12', 3, 1, 2), -- Nuke
    (1, 2, 4, 4, 2, '2024-08-13', 3, 0, 2), -- Inferno
    (2, 2, 1, 2, 8, '2024-03-24', 3, 2, 1), -- Anubis historical
    (2, 4, 3, 4, 1, '2024-03-25', 3, 2, 0); -- Mirage

INSERT INTO tournament_results (tournament_id, team_id, placement, earnings) VALUES
    (1, 3, 1, 400000),
    (1, 4, 2, 180000),
    (1, 1, 3, 80000),
    (1, 2, 4, 40000),
    (2, 2, 1, 500000),
    (2, 4, 2, 170000),
    (2, 1, 3, 80000),
    (2, 3, 4, 40000);

INSERT INTO team_roster (team_id, player_id, is_active, start_date) VALUES
    (1, 1, TRUE, '2024-01-01'),
    (1, 2, TRUE, '2024-01-01'),
    (2, 3, TRUE, '2024-01-01'),
    (2, 4, TRUE, '2024-01-01'),
    (3, 5, TRUE, '2024-01-01'),
    (3, 6, TRUE, '2024-01-01'),
    (4, 7, TRUE, '2024-01-01'),
    (4, 8, TRUE, '2024-01-01');
