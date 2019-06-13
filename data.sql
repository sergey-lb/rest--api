INSERT INTO users
(name)
VALUES ('Vasya'), ('Masha');

INSERT INTO projects
(owner_id, name)
VALUES(1, 'Sportmaster'), (2, 'Ulmart');

INSERT INTO issues
(subject, project_id, author_id, status)
VALUES('Search doesn''t work', 1, 1, 0);