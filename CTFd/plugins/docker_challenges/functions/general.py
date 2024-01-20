import logging
import tempfile
import traceback
from pathlib import Path
from typing import Optional, Tuple

import requests
from flask import Request

from CTFd.models import db

from ..models.models import DockerConfig

logger = logging.getLogger(__name__)


def do_request(
    docker: DockerConfig,
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    data: Optional[dict] = None,
) -> requests.Response:
    tls = docker.tls_enabled
    prefix = "https" if tls else "http"
    host = docker.hostname
    BASE_URL = f"{prefix}://{host}"
    if not headers:
        headers = {"Content-Type": "application/json"}
    if tls:
        if method == "DELETE":
            r = requests.delete(
                url=f"{BASE_URL}{url}",
                cert=(docker.client_cert, docker.client_key),
                verify=docker.ca_cert,
                headers=headers,
            )
        elif method == "POST":
            r = requests.post(
                url=f"{BASE_URL}{url}",
                cert=(docker.client_cert, docker.client_key),
                verify=docker.ca_cert,
                headers=headers,
                data=data,
            )
        else:
            r = requests.get(
                url=f"{BASE_URL}{url}",
                cert=(docker.client_cert, docker.client_key),
                verify=docker.ca_cert,
                headers=headers,
            )
    elif method == "DELETE":
        r = requests.delete(url=f"{BASE_URL}{url}", headers=headers)
    elif method == "POST":
        r = requests.post(url=f"{BASE_URL}{url}", headers=headers, data=data)
    else:
        r = requests.get(url=f"{BASE_URL}{url}", headers=headers)
    return r


# For the Docker Config Page. Gets the Current Repositories available on the Docker Server.
def get_repositories(
    docker: DockerConfig, tags: bool = False, repos: bool = False
) -> list:
    r = do_request(docker, "/images/json?all=1")
    result = []
    for i in r.json():
        if i["RepoTags"] is not None and i["RepoTags"][0].split(":")[0] != "<none>":
            if repos and i["RepoTags"][0].split(":")[0] not in repos:
                continue
            if not tags:
                result.append(i["RepoTags"][0].split(":")[0])
            else:
                result.append(i["RepoTags"][0])
    return list(set(result))


def get_secrets(docker):
    r = do_request(docker, "/secrets")
    tmplist = []
    for secret in r.json():
        tmpdict = {"ID": secret["ID"], "Name": secret["Spec"]["Name"]}
        tmplist.append(tmpdict)
    return tmplist


def delete_secret(docker: DockerConfig, id: str):
    r = do_request(docker, f"/secrets/{id}", method="DELETE")
    return r.ok


def get_unavailable_ports(docker):
    r = do_request(docker, "/containers/json?all=1")
    result = []
    for i in r.json():
        if i["Ports"] != []:
            result.extend(p["PublicPort"] for p in i["Ports"] if p.get("PublicPort"))
    r = do_request(docker, "/services?all=1")
    for i in r.json():
        endpoint = i["Endpoint"]["Spec"]
        if endpoint != {}:
            result.extend(
                p["PublishedPort"] for p in endpoint["Ports"] if p.get("PublishedPort")
            )
    return result


def get_required_ports(docker, image):
    r = do_request(docker, f"/images/{image}/json?all=1")
    return r.json()["Config"]["ExposedPorts"].keys()


def create_temp_file(in_file: bytes) -> str:
    """Create temp file and  return temp name."""
    temp_file = tempfile.NamedTemporaryFile(mode="wb", dir="/tmp", delete=False)
    temp_file.write(in_file)
    temp_file.seek(0)
    return temp_file.name


def get_file(request: Request, file_name: str) -> bytes:
    contents = request.files.get(file_name)
    return contents.stream.read() if contents else b""


def create_docker_config(
    request: Request, docker: Optional[DockerConfig]
) -> DockerConfig:
    docker = docker or DockerConfig()
    docker.hostname = request.form["hostname"]
    docker.tls_enabled = request.form["tls_enabled"]
    docker.tls_enabled = docker.tls_enabled == "True"
    if docker.tls_enabled:
        docker.ca_cert, docker.client_cert, docker.client_key = create_tls_files(
            request=request
        )
    else:
        docker.ca_cert = None
        docker.client_cert = None
        docker.client_key = None
    repositories = request.form.to_dict(flat=False).get("repositories")
    print(repositories)
    docker.repositories = ",".join(repositories) if repositories else None
    db.session.add(docker)
    db.session.commit()
    return DockerConfig.query.filter_by(id=1).first()


def create_tls_files(request: Request, docker: DockerConfig) -> Tuple[str, str, str]:
    ca_cert = get_file(request=request, file_name="ca_cert")
    client_cert = get_file(request=request, file_name="client_cert")
    client_key = get_file(request=request, file_name="client_key")
    req_files = all((ca_cert, client_cert, client_key))
    config_files = (docker.ca_cert, docker.client_cert, docker.client_key)
    if req_files:
        return (
            create_temp_file(in_file=ca_cert),
            create_temp_file(in_file=client_cert),
            create_temp_file(in_file=client_key),
        )
    elif all((Path(config).exists() for config in config_files)):
        return config_files
    else:
        raise ValueError("Missing required TLS files.")
