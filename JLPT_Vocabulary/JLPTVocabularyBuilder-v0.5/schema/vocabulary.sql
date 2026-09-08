PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    license TEXT,
    retrieved_at TEXT
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY,
    jmdict_entry_id INTEGER,
    word TEXT NOT NULL,
    reading TEXT NOT NULL DEFAULT '',
    jlpt_level INTEGER NOT NULL CHECK (jlpt_level BETWEEN 1 AND 5),

    primary_pos TEXT,
    pos_group TEXT,
    pos_zh TEXT,

    verb_class TEXT,
    transitivity TEXT,
    adjective_class TEXT,

    is_common INTEGER NOT NULL DEFAULT 0 CHECK (is_common IN (0,1)),
    common_score INTEGER NOT NULL DEFAULT 0,
    common_rank INTEGER,

    match_method TEXT,
    match_score REAL,

    source_id INTEGER,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_vocab_word_reading_level
ON vocabulary(word, reading, jlpt_level);
CREATE INDEX IF NOT EXISTS idx_vocab_jlpt_level ON vocabulary(jlpt_level);
CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocabulary(word);
CREATE INDEX IF NOT EXISTS idx_vocab_reading ON vocabulary(reading);
CREATE INDEX IF NOT EXISTS idx_vocab_jmdict_entry ON vocabulary(jmdict_entry_id);
CREATE INDEX IF NOT EXISTS idx_vocab_pos_group ON vocabulary(pos_group);
CREATE INDEX IF NOT EXISTS idx_vocab_common_score ON vocabulary(common_score DESC);
CREATE INDEX IF NOT EXISTS idx_vocab_common_rank ON vocabulary(common_rank);

CREATE TABLE IF NOT EXISTS senses (
    id INTEGER PRIMARY KEY,
    vocabulary_id INTEGER NOT NULL,
    jmdict_sense_index INTEGER NOT NULL,
    meaning_en TEXT,
    meaning_zh TEXT,
    pos_text TEXT,
    pos_group TEXT,
    pos_zh TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
    review_status TEXT NOT NULL DEFAULT 'pending',
    translation_source TEXT,
    translation_note TEXT,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE,
    UNIQUE(vocabulary_id, jmdict_sense_index)
);

CREATE INDEX IF NOT EXISTS idx_senses_vocab ON senses(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_senses_review ON senses(review_status);

CREATE TABLE IF NOT EXISTS meanings (
    id INTEGER PRIMARY KEY,
    vocabulary_id INTEGER NOT NULL,
    language TEXT NOT NULL,
    meaning TEXT NOT NULL,
    sense_index INTEGER NOT NULL DEFAULT 0,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY,
    vocabulary_id INTEGER NOT NULL,
    sense_id INTEGER,
    sentence_ja TEXT NOT NULL,
    sentence_zh TEXT,
    sentence_en TEXT,
    source TEXT,
    source_external_id TEXT,
    difficulty INTEGER,
    sense_match_method TEXT,
    sense_match_score REAL,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE,
    FOREIGN KEY (sense_id) REFERENCES senses(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_examples_vocab ON examples(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_examples_sense ON examples(sense_id);

CREATE TABLE IF NOT EXISTS distractor_features (
    vocabulary_id INTEGER PRIMARY KEY,

    same_level INTEGER NOT NULL DEFAULT 1,
    pos_group TEXT,
    pos_zh TEXT,

    reading_length INTEGER,
    mora_bucket INTEGER,

    script_type TEXT,                 -- kanji/kana/mixed
    has_kanji INTEGER NOT NULL DEFAULT 0,
    first_char TEXT,
    last_char TEXT,

    meaning_keywords TEXT,            -- normalized Chinese keywords for semantic-near distractors
    sense_count INTEGER NOT NULL DEFAULT 0,

    common_score INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_distractor_pos ON distractor_features(pos_group);
CREATE INDEX IF NOT EXISTS idx_distractor_level_common
ON distractor_features(same_level, common_score DESC);
CREATE INDEX IF NOT EXISTS idx_distractor_script ON distractor_features(script_type);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS vocabulary_tags (
    vocabulary_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (vocabulary_id, tag_id),
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS word_lists (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    source TEXT
);

CREATE TABLE IF NOT EXISTS word_list_items (
    word_list_id INTEGER NOT NULL,
    vocabulary_id INTEGER NOT NULL,
    sort_order INTEGER,
    PRIMARY KEY (word_list_id, vocabulary_id),
    FOREIGN KEY (word_list_id) REFERENCES word_lists(id) ON DELETE CASCADE,
    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS vocabulary_fts USING fts5(
    vocabulary_id UNINDEXED,
    word,
    reading,
    meaning_zh,
    meaning_en,
    tokenize = 'unicode61'
);
