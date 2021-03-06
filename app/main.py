import os

import waitress
from flask import Flask, render_template, request, jsonify
from app.db import Db
from urllib.parse import urlparse

if 'DATABASE_URL' in os.environ:
    conf = urlparse(os.environ['DATABASE_URL'])
    DB_CONF = {
        'db': conf.path[1:],
        'user': conf.username ,
        'pass': conf.password ,
        'host': conf.hostname,
        'port': conf.port
    }
else:
    DB_CONF = {
        'db': 'rest',
        'user': 'rest',
        'pass': 'Et4%gfdg##^f99h',
        'host': '192.168.99.100',
        'port': '5432'
    }

def start():
    app = Flask(__name__)

    db = Db(DB_CONF)

    @app.route('/api/users', methods=['GET'])
    def get_all_users():
        users = db.find_all('users')
        return jsonify(users)

    @app.route('/api/users/<int:user_id>', methods=['GET'])
    def get_user_by_id(user_id):
        user = db.find('users', user_id)
        if not user:
            return '', 404
        return jsonify(user)

    @app.route('/api/users', methods=['POST'])
    def save_user():
        data = request.get_json()
        if data['id'] == 0:
            del data['id']
            db.insert('users', data)
            return '', 200

        if not db.find('users', data['id']):
            return '', 404

        db.update('users', data)
        return '', 200

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    def remove_user_by_id(user_id):
        if not db.find('users', user_id):
            return '', 404

        db.delete('users', user_id)
        return '', 200

    @app.route('/api/users/<int:user_id>/projects', methods=['GET'])
    def get_users_projects(user_id):
        projects = db.find_by_column('projects', column='owner_id', value=user_id)
        return jsonify(projects)

    @app.route('/api/users/<int:user_id>/projects/<int:project_id>', methods=['GET'])
    def get_project_by_id(user_id, project_id):
        project = db.find('projects', project_id)
        if not project or project['owner_id'] != user_id:
            return '', 404

        return jsonify(project)

    @app.route('/api/users/<int:user_id>/projects', methods=['POST'])
    def save_project(user_id):
        data = request.get_json()
        if data['id'] == 0:
            if not db.find('users', user_id):
                return '', 404
            del data['id']
            data['owner_id'] = user_id
            db.insert('projects', data)
            return '', 200

        project = db.find('projects', data['id'])
        if not project or project['owner_id'] != user_id:
            return '', 404

        data['owner_id'] = user_id
        db.update('projects', data)
        return '', 200

    @app.route('/api/users/<int:user_id>/projects/<int:project_id>', methods=['DELETE'])
    def remove_project_by_id(user_id, project_id):
        project = db.find('projects', project_id)
        if not project or project['owner_id'] != user_id:
            return '', 404
        db.delete('projects', project_id)
        return '', 200

    @app.route('/api/users/<int:user_id>/projects/<int:project_id>/issues', methods=['GET'])
    def get_projects_issues(user_id, project_id):
        sql = """
            SELECT i.* FROM issues i
            INNER JOIN projects p
            ON p.id = i.project_id
            WHERE p.owner_id = %(owner_id)s
            AND i.project_id = %(project_id)s
        """

        issues = db.raw(sql, {
            "owner_id": user_id,
            "project_id": project_id
        }).fetchall()

        if not len(issues):
            return jsonify(issues)

        issue_ids = []
        for issue in issues:
            issue_ids.append(issue['id'])

        sorting = {
            'column': 'label',
            'order': 'ASC'
        }

        labels = db.find_by_column_in('labels', column='issue_id', values=issue_ids, sorting=sorting)
        labels_by_issue_id = {}
        for label in labels:
            if not label['issue_id'] in labels_by_issue_id:
                labels_by_issue_id[label['issue_id']] = []
            labels_by_issue_id[label['issue_id']].append(label['label'])

        sorting = {
            'column': 'user_id',
            'order': 'ASC'
        }

        assignees = db.find_by_column_in('assignees', column='issue_id', values=issue_ids, sorting=sorting)
        assignees_by_issue_id = {}
        for assignee in assignees:
            if not assignee['issue_id'] in assignees_by_issue_id:
                assignees_by_issue_id[assignee['issue_id']] = []
            assignees_by_issue_id[assignee['issue_id']].append(assignee['user_id'])

        for issue in issues:
            if issue['id'] in labels_by_issue_id:
                issue['labels'] = labels_by_issue_id[issue['id']]
            else:
                issue['labels'] = []

            if issue['id'] in assignees_by_issue_id:
                issue['assignees'] = assignees_by_issue_id[issue['id']]
            else:
                issue['assignees'] = []

        return jsonify(issues)

    @app.route('/api/users/<int:user_id>/projects/<int:project_id>/issues/<int:issue_id>', methods=['GET'])
    def get_issue_by_id(user_id, project_id, issue_id):
        sql = """
                    SELECT i.* FROM issues i
                    INNER JOIN projects p
                    ON p.id = i.project_id
                    WHERE p.owner_id = %(owner_id)s
                    AND i.project_id = %(project_id)s
                    AND i.id = %(issue_id)s
                """
        issue = db.raw(sql, {
            "owner_id": user_id,
            "project_id": project_id,
            "issue_id": issue_id
        }).fetchone()

        sorting = {
            'column': 'label',
            'order': 'ASC'
        }

        labels = db.find_by_column('labels', column='issue_id', value=issue_id, sorting=sorting)
        labels=list(map(lambda x: x['label'], labels))

        sorting = {
            'column': 'user_id',
            'order': 'ASC'
        }

        assignees = db.find_by_column('assignees', column='issue_id', value=issue_id, sorting=sorting)
        assignees = list(map(lambda x: x['user_id'], assignees))

        issue['labels'] = labels
        issue['assignees'] = assignees

        return jsonify(issue)

    @app.route('/api/users/<int:user_id>/projects/<int:project_id>/issues', methods=['POST'])
    def save_issue(user_id, project_id):
        project = db.find('projects', project_id)
        if not project or project['owner_id'] != user_id:
            return '', 404

        data = request.get_json()
        data['author_id'] = user_id
        data['project_id'] = project_id

        data_to_save = data.copy()
        del data_to_save['labels']
        del data_to_save['assignees']

        if data['id'] == 0:
            del data_to_save['id']
            issue_id = db.insert('issues', data_to_save)
            if 'labels' in data:
                save_labels(issue_id, data['labels'])
            if 'assignees' in data:
                save_assignees(issue_id, data['assignees'])
            return '', 200

        issue = db.find('issues', data['id'])
        if not issue or issue['project_id'] != project_id:
            return '', 404

        data['project_id'] = project_id
        db.update('issues', data_to_save)

        if 'labels' in data:
            save_labels(data['id'], data['labels'])

        if 'assignees' in data:
            save_assignees(data['id'], data['assignees'])

        return '', 200

    @app.route('/api/users/<int:user_id>/projects/<int:project_id>/issues/<int:issue_id>', methods=['DELETE'])
    def remove_issue_by_id(user_id, project_id, issue_id):
        sql = """
                            SELECT i.* FROM issues i
                            INNER JOIN projects p
                            ON p.id = i.project_id
                            WHERE p.owner_id = %(owner_id)s
                            AND i.project_id = %(project_id)s
                            AND i.id = %(issue_id)s
                        """
        issue = db.raw(sql, {
            "owner_id": user_id,
            "project_id": project_id,
            "issue_id": issue_id
        }).fetchone()
        if not issue:
            return '', 404

        db.delete('issues', issue_id)
        return '', 200

    def save_labels(issue_id, labels):
        db.raw("DELETE FROM labels WHERE issue_id = %(issue_id)s", {"issue_id": issue_id})
        for label in labels:
            db.raw("INSERT INTO labels (issue_id, label) VALUES(%(issue_id)s, %(label)s)", {
                "issue_id": issue_id,
                "label": label
            })

    def save_assignees(issue_id, assignees):
        db.raw("DELETE FROM assignees WHERE issue_id = %(issue_id)s", {"issue_id": issue_id})
        for assignee in assignees:
            if not db.find('users', assignee):
                continue
            db.raw("INSERT INTO assignees (issue_id, user_id) VALUES(%(issue_id)s, %(user_id)s)", {
                "issue_id": issue_id,
                "user_id": assignee
            })

    if os.getenv('APP_ENV') == 'PROD' and os.getenv('PORT'):
        waitress.serve(app, port=os.getenv('PORT'))
    else:
        app.run(host='0.0.0.0', port=9876, debug=True)


if __name__ == '__main__':
    start()
