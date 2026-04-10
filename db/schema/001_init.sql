create table providers (
    provider_id bigserial primary key,
    code text not null unique,
    name text not null,
    base_reference text
);

create table ingestion_runs (
    ingestion_run_id bigserial primary key,
    provider_id bigint not null references providers(provider_id),
    entity_type text not null,
    source_path text not null,
    status text not null default 'pending' check (status in ('pending', 'running', 'completed', 'failed')),
    records_seen integer not null default 0,
    records_written integer not null default 0,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    error_text text
);

create table competitions (
    competition_id bigserial primary key,
    provider_id bigint not null references providers(provider_id),
    external_id text not null,
    name text not null,
    country_name text,
    competition_gender text,
    metadata jsonb not null default '{}'::jsonb,
    unique (provider_id, external_id)
);

create table seasons (
    season_id bigserial primary key,
    provider_id bigint not null references providers(provider_id),
    competition_id bigint not null references competitions(competition_id),
    external_id text not null,
    name text not null,
    start_date date,
    end_date date,
    metadata jsonb not null default '{}'::jsonb,
    unique (provider_id, external_id)
);

create table teams (
    team_id bigserial primary key,
    provider_id bigint not null references providers(provider_id),
    external_id text not null,
    name text not null,
    short_name text,
    country_name text,
    team_type text,
    metadata jsonb not null default '{}'::jsonb,
    unique (provider_id, external_id)
);

create table players (
    player_id bigserial primary key,
    provider_id bigint not null references providers(provider_id),
    external_id text not null,
    name text not null,
    display_name text,
    country_name text,
    birth_date date,
    dominant_foot text,
    primary_position text,
    position_group text,
    metadata jsonb not null default '{}'::jsonb,
    unique (provider_id, external_id)
);

create table matches (
    match_id bigserial primary key,
    provider_id bigint not null references providers(provider_id),
    external_id text not null,
    competition_id bigint not null references competitions(competition_id),
    season_id bigint not null references seasons(season_id),
    match_date date not null,
    kickoff_at timestamptz,
    home_team_id bigint not null references teams(team_id),
    away_team_id bigint not null references teams(team_id),
    home_score integer,
    away_score integer,
    stadium_name text,
    referee_name text,
    match_week integer,
    metadata jsonb not null default '{}'::jsonb,
    unique (provider_id, external_id),
    check (home_team_id <> away_team_id)
);

create table lineups (
    lineup_id bigserial primary key,
    match_id bigint not null references matches(match_id) on delete cascade,
    team_id bigint not null references teams(team_id),
    player_id bigint not null references players(player_id),
    jersey_number integer,
    position_name text,
    position_group text,
    is_starter boolean not null default false,
    start_minute smallint not null default 0,
    end_minute smallint not null default 120,
    metadata jsonb not null default '{}'::jsonb,
    unique (match_id, team_id, player_id)
);

create table events (
    event_id bigserial primary key,
    match_id bigint not null references matches(match_id) on delete cascade,
    provider_id bigint not null references providers(provider_id),
    external_id text not null,
    index_in_match integer not null,
    period smallint not null,
    minute smallint not null,
    second smallint not null default 0,
    timestamp_ms integer,
    team_id bigint references teams(team_id),
    player_id bigint references players(player_id),
    possession_id integer,
    play_pattern text,
    event_type text not null,
    event_subtype text,
    outcome text,
    body_part text,
    technique text,
    under_pressure boolean not null default false,
    counterpress boolean not null default false,
    x_start numeric(6,2),
    y_start numeric(6,2),
    x_end numeric(6,2),
    y_end numeric(6,2),
    duration_seconds numeric(7,3),
    pass_recipient_player_id bigint references players(player_id),
    pass_height text,
    pass_length numeric(7,3),
    pass_angle numeric(8,5),
    shot_xg numeric(7,4),
    related_team_id bigint references teams(team_id),
    metadata jsonb not null default '{}'::jsonb,
    raw_event jsonb not null default '{}'::jsonb,
    unique (match_id, external_id),
    unique (match_id, index_in_match)
);

create table event_related_events (
    event_id bigint not null references events(event_id) on delete cascade,
    related_event_id bigint not null references events(event_id) on delete cascade,
    relation_type text not null default 'related',
    primary key (event_id, related_event_id, relation_type)
);

create table team_match_metrics (
    team_match_metric_id bigserial primary key,
    match_id bigint not null references matches(match_id) on delete cascade,
    team_id bigint not null references teams(team_id),
    metric_key text not null,
    metric_value numeric(14,4) not null,
    metric_context jsonb not null default '{}'::jsonb,
    computed_at timestamptz not null default now(),
    unique (match_id, team_id, metric_key)
);

create table player_match_metrics (
    player_match_metric_id bigserial primary key,
    match_id bigint not null references matches(match_id) on delete cascade,
    team_id bigint not null references teams(team_id),
    player_id bigint not null references players(player_id),
    metric_key text not null,
    metric_value numeric(14,4) not null,
    metric_context jsonb not null default '{}'::jsonb,
    computed_at timestamptz not null default now(),
    unique (match_id, player_id, metric_key)
);

create table tactical_reports (
    tactical_report_id bigserial primary key,
    scope_type text not null check (scope_type in ('match', 'team_window', 'comparison')),
    scope_key text not null,
    subject_team_id bigint references teams(team_id),
    match_id bigint references matches(match_id) on delete cascade,
    title text not null,
    summary text not null,
    evidence jsonb not null default '{}'::jsonb,
    report_version text not null default 'v1',
    created_at timestamptz not null default now()
);

create index idx_matches_date on matches (match_date desc);
create index idx_matches_teams on matches (home_team_id, away_team_id);
create index idx_events_match_team_type on events (match_id, team_id, event_type);
create index idx_events_match_possession on events (match_id, possession_id, index_in_match);
create index idx_events_player on events (player_id);
create index idx_team_metrics_lookup on team_match_metrics (team_id, metric_key, match_id desc);
create index idx_player_metrics_lookup on player_match_metrics (player_id, metric_key, match_id desc);
create index idx_tactical_reports_scope on tactical_reports (scope_type, scope_key);

insert into providers (code, name, base_reference)
values ('statsbomb', 'StatsBomb / event-data style provider', 'provider-configured')
on conflict (code) do nothing;
