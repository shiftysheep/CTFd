import tempfile
import traceback

from flask import Blueprint, render_template, request

from CTFd.api import CTFd_API_v1
from CTFd.models import Teams, Users, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import admins_only

from .api import (
    active_docker_namespace,
    container_namespace,
    docker_namespace,
    kill_container,
    secret_namespace,
)
from .functions.general import create_temp_file, get_file, get_repositories
from .models.container import DockerChallengeType
from .models.models import DockerChallengeTracker, DockerConfig, DockerConfigForm
from .models.service import DockerServiceChallengeType


def define_docker_admin(app):
    admin_docker_config = Blueprint(
        "admin_docker_config",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @admin_docker_config.route("/admin/docker_config", methods=["GET", "POST"])
    @admins_only
    def docker_config():
        docker = DockerConfig.query.filter_by(id=1).first()
        form = DockerConfigForm()
        if request.method == "POST":
            b = docker or DockerConfig()
            b.hostname = request.form["hostname"]
            b.tls_enabled = request.form["tls_enabled"]
            b.tls_enabled = b.tls_enabled == "True"
            if not b.tls_enabled:
                b.ca_cert = None
                b.client_cert = None
                b.client_key = None
            else:
                ca_cert = get_file(request=request, file_name="ca_cert")
                client_cert = get_file(request=request, file_name="client_cert")
                client_key = get_file(request=request, file_name="client_key")
                if ca_cert:
                    b.ca_cert = create_temp_file(in_file=ca_cert)
                if client_cert:
                    b.client_cert = create_temp_file(in_file=client_cert)
                if client_key:
                    b.client_key = create_temp_file(in_file=client_key)
            b.repositories = ",".join(
                request.form.to_dict(flat=False).get("repositories")
            )
            db.session.add(b)
            db.session.commit()
            docker = DockerConfig.query.filter_by(id=1).first()
        repos = get_repositories(docker) if docker else []
        if not repos:
            form.repositories.choices = [("ERROR", "No repositories available")]
        else:
            form.repositories.choices = [(d, d) for d in repos]
        dconfig = DockerConfig.query.first()
        selected_repos = dconfig.repositories
        if selected_repos is None:
            selected_repos = []
        return render_template(
            "docker_config.html", config=dconfig, form=form, repos=selected_repos
        )

    app.register_blueprint(admin_docker_config)


def define_docker_status(app):
    admin_docker_status = Blueprint(
        "admin_docker_status",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @admin_docker_status.route("/admin/docker_status", methods=["GET", "POST"])
    @admins_only
    def docker_admin():
        # docker_config = DockerConfig.query.filter_by(id=1).first()
        docker_tracker = DockerChallengeTracker.query.all()
        for i in docker_tracker:
            if is_teams_mode():
                name = Teams.query.filter_by(id=i.team_id).first()
                i.team_id = name.name
            else:
                name = Users.query.filter_by(id=i.user_id).first()
                i.user_id = name.name
        return render_template("admin_docker_status.html", dockers=docker_tracker)

    app.register_blueprint(admin_docker_status)


def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["docker"] = DockerChallengeType
    CHALLENGE_CLASSES["docker_service"] = DockerServiceChallengeType
    register_plugin_assets_directory(app, base_path="/plugins/docker_challenges/assets")
    define_docker_admin(app)
    define_docker_status(app)
    CTFd_API_v1.add_namespace(docker_namespace, "/docker")
    CTFd_API_v1.add_namespace(container_namespace, "/container")
    CTFd_API_v1.add_namespace(active_docker_namespace, "/docker_status")
    CTFd_API_v1.add_namespace(kill_container, "/nuke")
    CTFd_API_v1.add_namespace(secret_namespace, "/secret")
