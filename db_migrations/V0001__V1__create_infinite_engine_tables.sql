
CREATE TABLE t_p12938855_infinite_engine_desi.projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    efficiency NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p12938855_infinite_engine_desi.components (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES t_p12938855_infinite_engine_desi.projects(id),
    type VARCHAR(100) NOT NULL,
    label VARCHAR(255),
    pos_x NUMERIC(8,2) DEFAULT 0,
    pos_y NUMERIC(8,2) DEFAULT 0,
    params JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p12938855_infinite_engine_desi.connections (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES t_p12938855_infinite_engine_desi.projects(id),
    from_component_id INTEGER REFERENCES t_p12938855_infinite_engine_desi.components(id),
    to_component_id INTEGER REFERENCES t_p12938855_infinite_engine_desi.components(id),
    flow_type VARCHAR(50) DEFAULT 'heat',
    value NUMERIC(12,4),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p12938855_infinite_engine_desi.calculations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES t_p12938855_infinite_engine_desi.projects(id),
    calc_type VARCHAR(100) NOT NULL,
    input_params JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    ai_explanation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p12938855_infinite_engine_desi.ai_chat (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES t_p12938855_infinite_engine_desi.projects(id),
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_components_project ON t_p12938855_infinite_engine_desi.components(project_id);
CREATE INDEX idx_connections_project ON t_p12938855_infinite_engine_desi.connections(project_id);
CREATE INDEX idx_calculations_project ON t_p12938855_infinite_engine_desi.calculations(project_id);
CREATE INDEX idx_chat_project ON t_p12938855_infinite_engine_desi.ai_chat(project_id);
