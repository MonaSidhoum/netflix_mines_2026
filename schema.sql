PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Genre (
    ID   INTEGER PRIMARY KEY AUTOINCREMENT,
    Type TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS Utilisateur (
    ID            INTEGER PRIMARY KEY AUTOINCREMENT,
    AdresseMail   TEXT    NOT NULL UNIQUE,
    Pseudo        TEXT    NOT NULL,
    MotDePasse    TEXT    NOT NULL  -- stocké haché (bcrypt, argon2…)
);

CREATE TABLE IF NOT EXISTS Film (
    ID           INTEGER PRIMARY KEY AUTOINCREMENT,
    Nom          TEXT    NOT NULL,
    Note         REAL,
    DateSortie   INTEGER,           -- année (ex: 2023)
    Image        TEXT,              -- URL
    Video        TEXT,              -- URL
    Genre_ID     INTEGER NOT NULL,
    FOREIGN KEY (Genre_ID) REFERENCES Genre(ID)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS Genre_Utilisateur (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Genre    INTEGER NOT NULL,
    ID_User     INTEGER NOT NULL,
    FOREIGN KEY (ID_Genre) REFERENCES Genre(ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (ID_User)  REFERENCES Utilisateur(ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (ID_Genre, ID_User)   -- évite les doublons
);